"""Punto de entrada para el actor de Apify.

Lee el input del key-value store de Apify (INPUT), genera el dataset sintético
y escribe los archivos de salida (users, goals, transactions) al key-value store.
"""
from __future__ import annotations

import io
import json
import os
from datetime import date, datetime

from apify import Actor

from latam_synth import GeneratorConfig, SyntheticGenerator


def _parse_date(s: str | None, default: date) -> date:
    if not s:
        return default
    return datetime.strptime(s, "%Y-%m-%d").date()


async def main() -> None:
    async with Actor:
        inp = await Actor.get_input() or {}

        users = int(inp.get("users", 1000))
        seed = inp.get("seed")
        countries = inp.get("countries") or None
        fmt = inp.get("format", "csv").lower()
        start_date = _parse_date(inp.get("start_date"), date(2023, 1, 1))
        end_date = _parse_date(inp.get("end_date"), date(2024, 12, 31))

        # Validaciones
        if not (1 <= users <= 50_000):
            raise ValueError(f"users debe estar entre 1 y 50,000 (recibido: {users})")

        Actor.log.info(f"Generando {users} usuarios | seed={seed} | formato={fmt}")

        cfg = GeneratorConfig(
            n_users=users,
            seed=seed,
            countries=countries,
            start_date=start_date,
            end_date=end_date,
        )
        data = SyntheticGenerator(cfg).generate()

        store = await Actor.open_key_value_store()

        if fmt == "json":
            def _to_records(df):
                return [
                    {k: (v.isoformat() if isinstance(v, date) else v) for k, v in row.items()}
                    for row in df.to_dict(orient="records")
                ]

            payload = {
                "meta": {
                    "users": len(data["users"]),
                    "goals": len(data["goals"]),
                    "transactions": len(data["transactions"]),
                    "seed": seed,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                },
                "users": _to_records(data["users"]),
                "goals": _to_records(data["goals"]),
                "transactions": _to_records(data["transactions"]),
            }
            await store.set_value("OUTPUT", payload, content_type="application/json")
            Actor.log.info("Resultado escrito: OUTPUT (JSON)")
        else:
            for table_name, df in data.items():
                buf = io.StringIO()
                df.to_csv(buf, index=False)
                key = f"{table_name}.csv"
                await store.set_value(key, buf.getvalue(), content_type="text/csv")
                Actor.log.info(f"Resultado escrito: {key} ({len(df):,} filas)")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
