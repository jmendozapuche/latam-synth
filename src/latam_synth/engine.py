"""Motor de generación sintética calibrado con comportamiento real LatAm 2015-2024.

v0.1: lognormales simples + muestreo directo de distribuciones categóricas.
v0.2: montos desde mezcla de lognormales + snap a valores redondos + trayectorias
temporales coherentes por meta (proceso de punto con intensidad decreciente).
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from importlib import resources
from typing import Optional

import numpy as np
import pandas as pd


def load_params() -> dict:
    with resources.files("latam_synth").joinpath("calibration_params.json").open() as f:
        return json.load(f)


@dataclass
class GeneratorConfig:
    n_users: int = 1000
    start_date: date = date(2023, 1, 1)
    end_date: date = date(2024, 12, 31)
    seed: Optional[int] = None
    countries: Optional[list[str]] = None  # None = mezcla calibrada completa
    goals_per_user_lambda: float = 1.2     # Poisson
    tx_per_goal_lambda: float = 2.8        # Poisson


class SyntheticGenerator:
    def __init__(self, config: GeneratorConfig | None = None):
        self.cfg = config or GeneratorConfig()
        self.P = load_params()
        self.rng = np.random.default_rng(self.cfg.seed)

    # ---------- users ----------
    def generate_users(self) -> pd.DataFrame:
        P, rng, n = self.P, self.rng, self.cfg.n_users
        geo = P["users"]["geo_mix"]
        if self.cfg.countries:
            geo = {k: v for k, v in geo.items() if k in self.cfg.countries}
        total = sum(geo.values())  # renormalizar siempre: geo_mix es top-12, no suma 1
        probs = [v / total for v in geo.values()]
        countries = rng.choice(list(geo.keys()), n, p=probs)

        # Scores correlacionados: gaussian copula sobre percentiles calibrados.
        corr = pd.DataFrame(P["users"]["score_correlations"]).values
        L = np.linalg.cholesky(corr + 1e-9 * np.eye(3))
        z = (L @ rng.standard_normal((3, n))).T
        from math import erf, sqrt
        u = 0.5 * (1 + np.vectorize(lambda x: erf(x / sqrt(2)))(z))

        def from_pct(uniform_col: np.ndarray, score_key: str) -> np.ndarray:
            pcts = P["users"]["scores"][score_key]
            xs = np.array([10, 25, 50, 75, 90, 99]) / 100
            ys = np.array([pcts[k] for k in ["10", "25", "50", "75", "90", "99"]])
            return np.interp(uniform_col, xs, ys)

        return pd.DataFrame({
            "user_id": [str(uuid.uuid4()) for _ in range(n)],
            "country": countries,
            "gamification_score": from_pct(u[:, 0], "gamification_score"),
            "savings_discipline_score": from_pct(u[:, 1], "savings_discipline_score"),
            "goals_completed_ratio": from_pct(u[:, 2], "goals_completed_ratio"),
        })

    # ---------- goals ----------
    def generate_goals(self, users: pd.DataFrame) -> pd.DataFrame:
        P, rng = self.P, self.rng
        cats = P["goals"]["categories"]
        cat_names = list(cats.keys())
        cat_shares = np.array([cats[c]["share"] for c in cat_names])
        cat_shares = cat_shares / cat_shares.sum()
        status_dist = P["goals"]["status_distribution"]

        rows = []
        span_days = (self.cfg.end_date - self.cfg.start_date).days
        for _, u in users.iterrows():
            for _ in range(rng.poisson(self.cfg.goals_per_user_lambda)):
                cat = rng.choice(cat_names, p=cat_shares)
                cp = cats[cat]
                lognorm = cp["required_amount_lognormal"]
                amount = float(np.clip(rng.lognormal(lognorm["mu"], lognorm["sigma"]), 50, 1e7))
                lo, hi = cp["horizon_days_iqr"] or [44, 268]
                horizon = int(rng.integers(max(int(lo * 0.5), 7), int(hi * 1.5)))
                created = self.cfg.start_date + timedelta(days=int(rng.integers(0, max(span_days, 1))))
                p_ach = cp["achieved_rate"]
                p_over = status_dist.get("overdue", 0.738) * (1 - p_ach) / (1 - 0.07)
                status = rng.choice(
                    ["achieved", "overdue", "in_progress"],
                    p=[p_ach, p_over, 1 - p_ach - p_over],
                )
                shared = rng.random() < P["goals"]["shared_share"]
                rows.append({
                    "goal_id": str(uuid.uuid4()),
                    "user_id": u["user_id"],
                    "category": cat,
                    "name": rng.choice(cp["sample_names"]) if cp["sample_names"] else cat,
                    "required_amount": round(amount, 2),
                    "created_at": created,
                    "deadline": created + timedelta(days=horizon),
                    "goal_status": status,
                    "is_shared": shared,
                })
        return pd.DataFrame(rows)

    # ---------- amounts ----------
    _SNAP_GRID = np.array([1, 1.5, 2, 2.5, 3, 4, 5, 6, 7.5, 8, 10], dtype=float)

    def _snap_to_round(self, x: float) -> float:
        mag = 10.0 ** np.floor(np.log10(max(x, 1e-9)))
        candidates = mag * self._SNAP_GRID
        return float(candidates[np.argmin(np.abs(candidates - x))])

    def _sample_amount(self, kind: str) -> float:
        mix = self.P["transactions"]["amount_mixture"][kind]
        w = np.asarray(mix["weights"])
        idx = self.rng.choice(mix["n_components"], p=w / w.sum())
        amount = float(np.exp(self.rng.normal(mix["mus"][idx], mix["sigmas"][idx])))
        amount = float(np.clip(amount, 0.01, 1e6))
        snap_cfg = self.P["transactions"]["round_snap"]
        if self.rng.random() < snap_cfg["snap_probability"]:
            amount = self._snap_to_round(amount)
        return amount

    # ---------- fechas con intensidad decreciente + estacionalidad ----------
    def _sample_dates_in_window(
        self,
        n: int,
        t_start: date,
        t_end: date,
        decay: float = 3.0,
    ) -> list[date]:
        """Muestrea n fechas en [t_start, t_end] con intensidad decreciente exp(-decay·u).

        Preserva estacionalidad mensual calibrada mediante rejection sampling ponderado
        por el peso del mes en la distribución real.
        """
        if n == 0:
            return []
        span = max((t_end - t_start).days, 1)
        seas = self.P["transactions"]["monthly_seasonality"]
        # Muestreo por rechazo: proponer días uniformes, aceptar con prob ∝ exp(-decay·u)
        # y peso de estacionalidad del mes. Máx iteraciones para garantizar n muestras.
        results: list[date] = []
        max_sea = max(seas.values())
        while len(results) < n:
            # Proponer día aleatorio en el rango
            day_offset = int(self.rng.integers(0, span + 1))
            d = t_start + timedelta(days=day_offset)
            # Peso intensidad decreciente
            u = day_offset / span
            intensity = float(np.exp(-decay * u))
            # Peso estacionalidad mensual (normalizado al máximo)
            month_weight = seas[str(d.month)] / max_sea
            # Aceptar con probabilidad proporcional al producto
            if self.rng.random() < intensity * month_weight:
                results.append(d)
        return results

    # ---------- transactions ----------
    def generate_transactions(self, goals: pd.DataFrame) -> pd.DataFrame:
        P, rng = self.P, self.rng
        dep_share = P["transactions"]["deposit_share"]

        rows = []
        for _, g in goals.iterrows():
            status = g["goal_status"]
            created: date = g["created_at"]
            deadline: date = g["deadline"]
            required: float = g["required_amount"]

            # Ventana efectiva según status
            if status == "in_progress":
                # Última transacción cerca del final del rango generado
                window_end = min(deadline, self.cfg.end_date)
            else:
                window_end = deadline

            window_start = max(created, self.cfg.start_date)
            if window_end <= window_start:
                # Meta fuera del rango de generación: sin transacciones
                continue

            if status == "achieved":
                self._gen_achieved(g, window_start, window_end, required, dep_share, rows)
            elif status == "overdue":
                self._gen_overdue(g, window_start, window_end, required, dep_share, rows)
            else:  # in_progress
                self._gen_in_progress(g, window_start, window_end, required, dep_share, rows)

        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=[
            "transaction_id", "goal_id", "user_id", "date",
            "transaction_type", "amount",
        ])

    def _make_row(self, g: pd.Series, d: date, is_dep: bool, amount: float) -> dict:
        return {
            "transaction_id": str(uuid.uuid4()),
            "goal_id": g["goal_id"],
            "user_id": g["user_id"],
            "date": d,
            "transaction_type": "deposit" if is_dep else "withdrawal",
            "amount": round(amount, 2),
        }

    def _gen_achieved(
        self, g: pd.Series, t0: date, t1: date, required: float,
        dep_share: float, rows: list,
    ) -> None:
        """Genera transacciones para meta achieved: depósitos netos >= required_amount.

        Genera transacciones regulares (montos del mixture) hasta cubrir required.
        Si los depósitos de las n_tx iniciales no alcanzan, añade depósitos adicionales
        con montos del mixture para mantener la distribución de montos intacta.
        """
        n_tx = max(1, self.rng.poisson(self.cfg.tx_per_goal_lambda))
        dates = self._sample_dates_in_window(n_tx, t0, t1, decay=2.0)
        dates.sort()
        net = 0.0
        for d in dates:
            is_dep = self.rng.random() < dep_share
            amount = self._sample_amount("deposit" if is_dep else "withdrawal")
            net += amount if is_dep else -amount
            rows.append(self._make_row(g, d, is_dep, amount))
        # Completar con depósitos adicionales del mixture hasta alcanzar required.
        # Máx 50 iteraciones para evitar bucles infinitos con required_amount muy alto.
        extra_iters = 0
        while net < required and extra_iters < 50:
            amount = self._sample_amount("deposit")
            net += amount
            rows.append(self._make_row(g, t1, True, amount))
            extra_iters += 1
        # Si aún no alcanza (required_amount extraordinariamente grande), depósito exacto.
        if net < required:
            top_up = round(required - net + 0.01, 2)
            rows.append(self._make_row(g, t1, True, top_up))

    def _gen_overdue(
        self, g: pd.Series, t0: date, t1: date, required: float,
        dep_share: float, rows: list,
    ) -> None:
        """Genera transacciones para meta overdue: depósitos netos < required, con
        intensidad decreciente fuerte que refleja el patrón de abandono real (73.8%).

        Si el neto supera required_amount por azar, reescala uniformemente todos los
        depósitos de la meta (factor < 1) para que el neto quede al 90% del target.
        No se añade ninguna transacción artificial detectable como huella sintética.
        """
        n_tx = max(1, self.rng.poisson(self.cfg.tx_per_goal_lambda))
        dates = self._sample_dates_in_window(n_tx, t0, t1, decay=4.0)
        dates.sort()
        goal_rows: list[dict] = []
        for d in dates:
            is_dep = self.rng.random() < dep_share
            amount = self._sample_amount("deposit" if is_dep else "withdrawal")
            goal_rows.append(self._make_row(g, d, is_dep, amount))

        total_dep = sum(r["amount"] for r in goal_rows if r["transaction_type"] == "deposit")
        total_wit = sum(r["amount"] for r in goal_rows if r["transaction_type"] == "withdrawal")
        net = total_dep - total_wit

        if net >= required and total_dep > 0:
            # Reescalado uniforme de todos los depósitos para que net quede al 99% de
            # required. Se clampea a 0.01 para evitar montos cero por redondeo.
            target_dep = required * 0.99 + total_wit
            factor = target_dep / total_dep
            for r in goal_rows:
                if r["transaction_type"] == "deposit":
                    r["amount"] = max(round(r["amount"] * factor, 2), 0.01)

        rows.extend(goal_rows)

    def _gen_in_progress(
        self, g: pd.Series, t0: date, t1: date, required: float,
        dep_share: float, rows: list,
    ) -> None:
        """Genera transacciones para meta in_progress: parcialmente fondedada,
        última transacción cerca del final del rango generado."""
        n_tx = max(1, self.rng.poisson(self.cfg.tx_per_goal_lambda))
        # decay bajo → actividad más sostenida, llega hasta el final del período
        dates = self._sample_dates_in_window(n_tx, t0, t1, decay=1.0)
        dates.sort()
        for d in dates:
            is_dep = self.rng.random() < dep_share
            amount = self._sample_amount("deposit" if is_dep else "withdrawal")
            rows.append(self._make_row(g, d, is_dep, amount))

    # ---------- full dataset ----------
    def generate(self) -> dict[str, pd.DataFrame]:
        users = self.generate_users()
        goals = self.generate_goals(users)
        txs = self.generate_transactions(goals)
        return {"users": users, "goals": goals, "transactions": txs}
