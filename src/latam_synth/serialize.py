"""Serialización JSON del dataset sintético, compartida por los adaptadores.

El motor (`engine.py`) devuelve DataFrames con objetos `date`. Cualquier capa que
exponga el dataset como JSON (MCP local, actor de Apify, API REST) necesita la
misma conversión y el mismo contrato de salida. Vive aquí para que no existan
tres versiones distintas.

Contrato: `generator` + `meta` (conteos de filas y parámetros) + las tres tablas
como listas de registros. Es el mismo que el registro `OUTPUT_DATA` del actor.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

GENERATOR_NAME = "LatAm Synth"


def _scalar(value: Any) -> Any:
    """Convierte tipos no serializables por json.dumps a primitivas."""
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "item"):  # np.int64, np.float64, np.bool_
        return value.item()
    return value


def records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """DataFrame -> lista de dicts JSON-serializables."""
    return [
        {key: _scalar(value) for key, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def dataset_payload(
    data: dict[str, pd.DataFrame],
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dataset completo -> payload JSON.

    `meta` añade claves al bloque de metadatos (seed, countries, transporte...)
    junto a los conteos de filas, que se calculan aquí.
    """
    tables = {name: records(frame) for name, frame in data.items()}
    return {
        "generator": GENERATOR_NAME,
        "meta": {
            "users": len(tables["users"]),
            "goals": len(tables["goals"]),
            "transactions": len(tables["transactions"]),
            **(meta or {}),
            "synthetic": True,
            "contains_pii": False,
        },
        "users": tables["users"],
        "goals": tables["goals"],
        "transactions": tables["transactions"],
    }
