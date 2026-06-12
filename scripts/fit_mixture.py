"""Calibración v0.2: mezcla de lognormales sobre log-montos del dataset fuente.

Uso (dev only, requiere el CSV fuente que NO está en el repo):
    python3 scripts/fit_mixture.py /ruta/a/enriched.csv

Aplica las mismas reglas de limpieza que la calibración v0.1 (ver
calibration_params.json -> meta.cleaning_rules): montos en (0, 1e6],
retiros ajustados sobre valor absoluto. Selecciona K en {2,3,4} por BIC,
valida KS y desvío de percentiles, e imprime el bloque JSON listo para
insertar bajo la clave `amount_mixture`.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.mixture import GaussianMixture

PCT_LEVELS = [1, 5, 10, 25, 50, 75, 90, 95, 99]


def load_amounts(csv_path: str) -> dict[str, np.ndarray]:
    df = pd.read_csv(
        csv_path,
        usecols=["amount", "data_type", "transaction_type"],
        dtype=str,
        low_memory=False,
    )
    tx = df[df["data_type"] == "transaction"].copy()
    tx["amount"] = pd.to_numeric(tx["amount"], errors="coerce")
    out = {}
    for kind in ("deposit", "withdrawal"):
        a = tx.loc[tx["transaction_type"] == kind, "amount"].abs()
        a = a[(a > 0) & (a <= 1e6)].dropna().to_numpy()
        out[kind] = a
    return out


def fit_best_mixture(amounts: np.ndarray, seed: int = 42) -> tuple[GaussianMixture, int]:
    """Selecciona K minimizando KS sobre log-montos (no BIC: los átomos en
    valores redondos del dato real sesgan el BIC hacia pocos componentes)."""
    x = np.log(amounts).reshape(-1, 1)
    rng = np.random.default_rng(seed)
    best, best_ks, best_k = None, np.inf, 0
    for k in (2, 3, 4, 5, 6):
        gm = GaussianMixture(n_components=k, n_init=8, random_state=seed).fit(x)
        sim = sample_mixture(
            gm.weights_.ravel(), gm.means_.ravel(),
            np.sqrt(gm.covariances_.ravel()), 300_000, rng,
        )
        ks = ks_2samp(np.log(amounts), np.log(np.clip(sim, None, 1e6))).statistic
        print(f"  K={k}: BIC={gm.bic(x):,.0f}  KS={ks:.4f}")
        if ks < best_ks:
            best, best_ks, best_k = gm, ks, k
    return best, best_k


def sample_mixture(weights, mus, sigmas, n, rng) -> np.ndarray:
    comp = rng.choice(len(weights), size=n, p=weights)
    return np.exp(rng.normal(np.asarray(mus)[comp], np.asarray(sigmas)[comp]))


def report(kind: str, real: np.ndarray, weights, mus, sigmas) -> dict:
    rng = np.random.default_rng(123)
    sim = sample_mixture(weights, mus, sigmas, 500_000, rng)
    sim = np.clip(sim, None, 1e6)
    ks = ks_2samp(np.log(real), np.log(sim)).statistic
    print(f"\n=== {kind} (n={len(real):,}) — KS log-montos: {ks:.4f} ===")
    print(f"  {'pctil':>6} {'real':>14} {'mezcla':>14} {'desvío':>8}")
    pcts = {}
    for p in PCT_LEVELS:
        qr, qs = np.percentile(real, p), np.percentile(sim, p)
        print(f"  {p:>5}% {qr:>14,.2f} {qs:>14,.2f} {(qs - qr) / qr * 100:>+7.1f}%")
        pcts[str(p)] = round(float(qr), 4)
    return {"ks_log": round(float(ks), 4), "percentiles_real": pcts}


def main(csv_path: str) -> None:
    amounts = load_amounts(csv_path)
    result = {}
    for kind, arr in amounts.items():
        print(f"\nAjustando {kind}...")
        gm, k = fit_best_mixture(arr)
        order = np.argsort(gm.means_.ravel())
        weights = gm.weights_.ravel()[order].tolist()
        mus = gm.means_.ravel()[order].tolist()
        sigmas = np.sqrt(gm.covariances_.ravel())[order].tolist()
        diag = report(kind, arr, weights, mus, sigmas)
        result[kind] = {
            "n_components": k,
            "weights": [round(w, 6) for w in weights],
            "mus": [round(m, 6) for m in mus],
            "sigmas": [round(s, 6) for s in sigmas],
            "fit_ks_log": diag["ks_log"],
        }

    print("\n\nBloque para calibration_params.json -> transactions.amount_mixture:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("uso: python3 scripts/fit_mixture.py <ruta_csv_fuente>")
    main(sys.argv[1])
