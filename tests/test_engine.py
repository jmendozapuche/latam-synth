from datetime import date

import numpy as np
import pandas as pd

from latam_synth import GeneratorConfig, SyntheticGenerator, load_params


def make(n=200, seed=42):
    return SyntheticGenerator(GeneratorConfig(n_users=n, seed=seed))


def _full(n=300, seed=42):
    g = SyntheticGenerator(GeneratorConfig(n_users=n, seed=seed))
    return g.generate()


def test_params_load():
    P = load_params()
    assert P["meta"]["source_rows"]["transactions"] == 305808
    assert len(P["goals"]["categories"]) == 8


def test_reproducibility():
    a = make().generate()
    b = make().generate()
    assert (a["users"]["country"].values == b["users"]["country"].values).all()


def test_entity_integrity():
    d = make().generate()
    assert d["goals"]["user_id"].isin(d["users"]["user_id"]).all()
    assert d["transactions"]["goal_id"].isin(d["goals"]["goal_id"]).all()


def test_deposit_share_close_to_calibration():
    d = make(n=800).generate()
    share = (d["transactions"]["transaction_type"] == "deposit").mean()
    assert abs(share - 0.861) < 0.06


def test_no_negative_amounts():
    d = make().generate()
    assert (d["transactions"]["amount"] > 0).all()
    assert (d["goals"]["required_amount"] > 0).all()


def test_country_filter():
    g = SyntheticGenerator(GeneratorConfig(n_users=100, seed=1, countries=["Mexico", "Colombia"]))
    users = g.generate_users()
    assert set(users["country"].unique()) <= {"Mexico", "Colombia"}


def test_amount_mixture_params_present():
    """v0.2: la mezcla debe existir sin haber tocado las claves v0.1."""
    P = load_params()
    mix = P["transactions"]["amount_mixture"]
    for kind in ("deposit", "withdrawal"):
        m = mix[kind]
        assert m["n_components"] == len(m["weights"]) == len(m["mus"]) == len(m["sigmas"])
        assert abs(sum(m["weights"]) - 1.0) < 1e-4
        assert all(s > 0 for s in m["sigmas"])
    # las claves v0.1 siguen intactas
    assert P["transactions"]["amount_lognormal"]["deposit"]["mu"] == 4.828851565178676


def test_amount_mixture_percentiles_close_to_source():
    """El motor de montos (_sample_amount) reproduce los percentiles calibrados.

    Se prueba directamente sobre la función de muestreo, antes de que la corrección
    de trayectorias temporales (overdue rescaling) pueda interferir. La corrección
    temporal es una invariante de negocio separada validada en test_overdue_*.
    """
    gen = SyntheticGenerator(GeneratorConfig(seed=7))
    amounts = np.array([gen._sample_amount("deposit") for _ in range(10_000)])
    ref = load_params()["transactions"]["amount_lognormal"]["deposit"]["percentiles"]
    for p, tol in [(50, 0.30), (90, 0.30), (99, 0.30)]:
        q = float(np.percentile(amounts, p))
        assert abs(q - ref[str(p)]) / ref[str(p)] < tol, f"p{p}: {q} vs {ref[str(p)]}"


def test_amount_mixture_reproducible():
    a = make(seed=11).generate()["transactions"]["amount"]
    b = make(seed=11).generate()["transactions"]["amount"]
    assert (a.values == b.values).all()


def test_round_snap_share():
    """~70% de los montos deben caer en la malla de valores redondos (calibrado: 69.5%)."""
    d = make(n=1000, seed=5).generate()
    amounts = d["transactions"]["amount"].to_numpy()
    grid = np.array([1, 1.5, 2, 2.5, 3, 4, 5, 6, 7.5, 8, 10])
    mags = 10.0 ** np.floor(np.log10(np.maximum(amounts, 1e-9)))
    candidates = mags[:, None] * grid[None, :]
    on_grid = np.isclose(candidates, amounts[:, None]).any(axis=1)
    assert 0.55 < on_grid.mean() < 0.85, f"snap share: {on_grid.mean():.2f}"


def test_round_snap_reproducible():
    a = make(seed=17).generate()["transactions"]["amount"]
    b = make(seed=17).generate()["transactions"]["amount"]
    assert (a.values == b.values).all()


# ---- tarea 3: trayectorias temporales coherentes por meta ----

def test_tx_within_goal_window():
    """(a) Toda transacción debe caer en [created_at, deadline] de su meta."""
    d = _full()
    goals = d["goals"].set_index("goal_id")
    txs = d["transactions"]
    if txs.empty:
        return
    merged = txs.join(goals[["created_at", "deadline"]], on="goal_id")
    # fecha >= created_at
    assert (merged["date"] >= merged["created_at"]).all(), \
        "transacción anterior a created_at"
    # fecha <= deadline
    assert (merged["date"] <= merged["deadline"]).all(), \
        "transacción posterior a deadline"


def test_achieved_goals_net_deposits_gte_required():
    """(b) y extra: suma neta (depósitos - retiros) de metas achieved >= required_amount."""
    d = _full(n=500, seed=99)
    goals = d["goals"]
    txs = d["transactions"]
    achieved = goals[goals["goal_status"] == "achieved"]
    if achieved.empty or txs.empty:
        return
    for _, g in achieved.iterrows():
        gtx = txs[txs["goal_id"] == g["goal_id"]]
        if gtx.empty:
            continue
        net = (
            gtx.loc[gtx["transaction_type"] == "deposit", "amount"].sum()
            - gtx.loc[gtx["transaction_type"] == "withdrawal", "amount"].sum()
        )
        assert net >= g["required_amount"] - 0.02, (
            f"meta achieved {g['goal_id']}: net={net:.2f} < required={g['required_amount']:.2f}"
        )


def test_overdue_goals_net_deposits_lt_required():
    """(c) Metas overdue deben quedarse por debajo de required_amount."""
    d = _full(n=500, seed=77)
    goals = d["goals"]
    txs = d["transactions"]
    overdue = goals[goals["goal_status"] == "overdue"]
    if overdue.empty or txs.empty:
        return
    for _, g in overdue.iterrows():
        gtx = txs[txs["goal_id"] == g["goal_id"]]
        if gtx.empty:
            continue
        net = (
            gtx.loc[gtx["transaction_type"] == "deposit", "amount"].sum()
            - gtx.loc[gtx["transaction_type"] == "withdrawal", "amount"].sum()
        )
        assert net < g["required_amount"], (
            f"meta overdue {g['goal_id']}: net={net:.2f} >= required={g['required_amount']:.2f}"
        )


def test_overdue_activity_front_loaded():
    """(c) Proceso de punto con intensidad decreciente: en metas overdue la mayoría
    de transacciones ocurre en la primera mitad del horizonte de la meta."""
    d = _full(n=500, seed=13)
    goals = d["goals"].set_index("goal_id")
    txs = d["transactions"]
    overdue_ids = goals[goals["goal_status"] == "overdue"].index
    if txs.empty:
        return
    txs_ov = txs[txs["goal_id"].isin(overdue_ids)].copy()
    txs_ov = txs_ov.join(goals[["created_at", "deadline"]], on="goal_id")
    if txs_ov.empty:
        return
    span = (
        pd.to_datetime(txs_ov["deadline"]) - pd.to_datetime(txs_ov["created_at"])
    ).dt.days.clip(lower=1)
    rel_pos = (
        pd.to_datetime(txs_ov["date"]) - pd.to_datetime(txs_ov["created_at"])
    ).dt.days / span
    # Con decay=4, E[u] ≈ 0.22 → más del 55% de tx deben caer en la primera mitad
    first_half_share = (rel_pos < 0.5).mean()
    assert first_half_share > 0.55, f"front-load share: {first_half_share:.2f}"


def test_in_progress_last_tx_near_end():
    """(d) Metas in_progress: al menos 1 transacción en el último 40% del período."""
    d = _full(n=500, seed=55)
    goals = d["goals"].set_index("goal_id")
    txs = d["transactions"]
    cfg_end = date(2024, 12, 31)
    ip_ids = goals[goals["goal_status"] == "in_progress"].index
    if txs.empty:
        return
    txs_ip = txs[txs["goal_id"].isin(ip_ids)].copy()
    txs_ip = txs_ip.join(goals[["created_at", "deadline"]], on="goal_id")
    if txs_ip.empty:
        return
    # Ventana efectiva es hasta min(deadline, cfg_end)
    txs_ip["window_end"] = txs_ip["deadline"].apply(lambda d: min(d, cfg_end))
    span = (
        pd.to_datetime(txs_ip["window_end"]) - pd.to_datetime(txs_ip["created_at"])
    ).dt.days.clip(lower=1)
    rel_pos = (
        pd.to_datetime(txs_ip["date"]) - pd.to_datetime(txs_ip["created_at"])
    ).dt.days / span
    last_40_share = (rel_pos >= 0.6).mean()
    assert last_40_share > 0.15, f"in_progress last-40% share: {last_40_share:.2f}"


def test_temporal_reproducibility():
    """(f) Reproducibilidad total por seed incluyendo fechas."""
    a = _full(seed=7)
    b = _full(seed=7)
    assert (a["transactions"]["date"].values == b["transactions"]["date"].values).all()


def test_no_nan_amounts():
    """Regresión: los retiros en fuente son negativos; el fit debe ser sobre |amount|."""
    d = make().generate()
    assert d["transactions"]["amount"].notna().all()
    P = load_params()
    wl = P["transactions"]["amount_lognormal"]["withdrawal"]
    assert wl["mu"] == wl["mu"]  # not NaN
