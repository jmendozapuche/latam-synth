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


def test_no_nan_amounts():
    """Regresión: los retiros en fuente son negativos; el fit debe ser sobre |amount|."""
    d = make().generate()
    assert d["transactions"]["amount"].notna().all()
    P = load_params()
    wl = P["transactions"]["amount_lognormal"]["withdrawal"]
    assert wl["mu"] == wl["mu"]  # not NaN
