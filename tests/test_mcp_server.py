"""Tests del servidor MCP local: registro de herramientas, validación de
argumentos y contrato del payload (mismas relaciones que el resto de caminos)."""
import asyncio
import json

import pytest

pytest.importorskip("mcp", reason="requiere el extra [mcp]")

from latam_synth.mcp_server import (  # noqa: E402
    MAX_USERS,
    describe_latam_synth_dataset,
    generate_latam_financial_data,
    mcp,
)


def _call(fn, **kwargs):
    """Invoca la función subyacente, esté o no envuelta por FastMCP."""
    target = getattr(fn, "fn", fn)
    return target(**kwargs)


# ---------- registro ----------

def test_tools_registered():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert {"generate_latam_financial_data", "describe_latam_synth_dataset"} <= names


def test_generate_tool_schema():
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    schema = tools["generate_latam_financial_data"].input_schema
    assert set(schema["properties"]) == {
        "users", "seed", "countries", "start_date", "end_date",
    }
    # todos los argumentos tienen default -> el agente puede llamar sin parámetros
    assert not schema.get("required")
    assert tools["generate_latam_financial_data"].description


def test_describe_tool_takes_no_arguments():
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    assert not tools["describe_latam_synth_dataset"].input_schema.get("properties")


# ---------- validación ----------

@pytest.mark.parametrize("users", [0, -5, MAX_USERS + 1])
def test_users_out_of_range(users):
    with pytest.raises(ValueError, match="between 1 and"):
        _call(generate_latam_financial_data, users=users)


def test_bad_date_format():
    with pytest.raises(ValueError, match="ISO format"):
        _call(generate_latam_financial_data, users=2, start_date="01/01/2023")


def test_end_date_before_start_date():
    with pytest.raises(ValueError, match="later than"):
        _call(
            generate_latam_financial_data,
            users=2,
            start_date="2024-01-01",
            end_date="2023-01-01",
        )


# ---------- contrato del payload ----------

def test_payload_shape_and_meta():
    """Mismo contrato que el registro OUTPUT_DATA del actor: generator + meta
    con conteos de filas + las tres tablas."""
    out = _call(generate_latam_financial_data, users=10, seed=42)
    assert set(out) == {"generator", "meta", "users", "goals", "transactions"}
    assert out["generator"] == "LatAm Synth"
    meta = out["meta"]
    assert meta["users"] == len(out["users"]) == 10
    assert meta["goals"] == len(out["goals"])
    assert meta["transactions"] == len(out["transactions"])
    assert meta["seed"] == 42
    assert meta["transport"] == "mcp-local"
    assert meta["synthetic"] is True and meta["contains_pii"] is False


def test_referential_integrity():
    out = _call(generate_latam_financial_data, users=25, seed=7)
    user_ids = {u["user_id"] for u in out["users"]}
    goal_ids = {g["goal_id"] for g in out["goals"]}
    assert all(g["user_id"] in user_ids for g in out["goals"])
    assert all(t["goal_id"] in goal_ids for t in out["transactions"])
    assert all(t["user_id"] in user_ids for t in out["transactions"])


def test_json_serializable_and_iso_dates():
    out = _call(generate_latam_financial_data, users=5, seed=3)
    json.dumps(out)  # no debe lanzar: sin date/Timestamp/np.* crudos
    goal = out["goals"][0]
    assert goal["created_at"] == str(goal["created_at"])
    assert len(goal["created_at"]) == 10 and goal["created_at"][4] == "-"
    assert len(out["transactions"][0]["date"]) == 10


def test_same_seed_same_dataset():
    a = _call(generate_latam_financial_data, users=15, seed=99)
    b = _call(generate_latam_financial_data, users=15, seed=99)
    assert [u["country"] for u in a["users"]] == [u["country"] for u in b["users"]]
    assert len(a["transactions"]) == len(b["transactions"])
    assert [t["amount"] for t in a["transactions"]] == [
        t["amount"] for t in b["transactions"]
    ]


def test_country_filter_applied():
    out = _call(
        generate_latam_financial_data,
        users=20,
        seed=5,
        countries=["Colombia", "Mexico"],
    )
    assert {u["country"] for u in out["users"]} <= {"Colombia", "Mexico"}


def test_custom_window_bounds_transactions():
    out = _call(
        generate_latam_financial_data,
        users=20,
        seed=11,
        start_date="2024-01-01",
        end_date="2024-06-30",
    )
    assert all(t["date"] >= "2024-01-01" for t in out["transactions"])


def test_describe_returns_schema():
    out = _call(describe_latam_synth_dataset)
    assert set(out["tables"]) == {"users", "goals", "transactions"}
    assert "Colombia" in out["countries"]
    assert out["max_users_per_call"] == MAX_USERS
    assert len(out["goal_categories"]) == 8
