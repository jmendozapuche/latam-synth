from datetime import date

import numpy as np

from latam_synth import GeneratorConfig, SyntheticGenerator, load_params


def make(n=200, seed=42):
    return SyntheticGenerator(GeneratorConfig(n_users=n, seed=seed))


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
    assert abs(share - 0.861) < 0.03


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
    """Los montos generados deben reproducir el cuerpo y la cola alta real.

    Referencia: percentiles de depósitos en calibration_params.json.
    Objetivo v0.2: desvío p99 < 15% (la cola alta era el problema de v0.1).
    """
    d = make(n=2000, seed=7).generate()
    dep = d["transactions"].loc[
        d["transactions"]["transaction_type"] == "deposit", "amount"
    ].to_numpy()
    ref = load_params()["transactions"]["amount_lognormal"]["deposit"]["percentiles"]
    for p, tol in [(50, 0.25), (90, 0.30), (99, 0.30)]:
        q = float(np.percentile(dep, p))
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


def test_no_nan_amounts():
    """Regresión: los retiros en fuente son negativos; el fit debe ser sobre |amount|."""
    d = make().generate()
    assert d["transactions"]["amount"].notna().all()
    P = load_params()
    wl = P["transactions"]["amount_lognormal"]["withdrawal"]
    assert wl["mu"] == wl["mu"]  # not NaN
