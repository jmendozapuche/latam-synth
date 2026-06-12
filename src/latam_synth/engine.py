"""Motor de generación sintética calibrado con comportamiento real LatAm 2015-2024.

v0.1: lognormales simples + muestreo directo de distribuciones categóricas.
v0.2 (ver CLAUDE.md): mezcla de lognormales + snap a montos redondos para la cola alta.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
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
    tx_per_goal_lambda: float = 2.8        # Poisson, calibrar en v0.2 contra fuente


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
                # Status: usa tasa de logro por categoría, resto se reparte overdue/in_progress
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

    # ---------- transactions ----------
    def generate_transactions(self, goals: pd.DataFrame) -> pd.DataFrame:
        P, rng = self.P, self.rng
        dl = P["transactions"]["amount_lognormal"]["deposit"]
        wl = P["transactions"]["amount_lognormal"]["withdrawal"]
        dep_share = P["transactions"]["deposit_share"]
        seas = P["transactions"]["monthly_seasonality"]
        months = np.array([int(k) for k in seas.keys()])
        month_p = np.array(list(seas.values()))
        month_p = month_p / month_p.sum()

        rows = []
        for _, g in goals.iterrows():
            n_tx = rng.poisson(self.cfg.tx_per_goal_lambda)
            for _ in range(n_tx):
                is_dep = rng.random() < dep_share
                ln = dl if is_dep else wl
                amount = float(np.clip(rng.lognormal(ln["mu"], ln["sigma"]), 0.01, 1e6))
                month = int(rng.choice(months, p=month_p))
                year = int(rng.integers(self.cfg.start_date.year, self.cfg.end_date.year + 1))
                day = int(rng.integers(1, 28))
                rows.append({
                    "transaction_id": str(uuid.uuid4()),
                    "goal_id": g["goal_id"],
                    "user_id": g["user_id"],
                    "date": date(year, month, day),
                    "transaction_type": "deposit" if is_dep else "withdrawal",
                    "amount": round(amount, 2),
                })
        return pd.DataFrame(rows)

    # ---------- full dataset ----------
    def generate(self) -> dict[str, pd.DataFrame]:
        users = self.generate_users()
        goals = self.generate_goals(users)
        txs = self.generate_transactions(goals)
        return {"users": users, "goals": goals, "transactions": txs}
