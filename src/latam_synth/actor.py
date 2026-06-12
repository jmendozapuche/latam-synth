"""Punto de entrada para el actor de Apify.

Lee el input del key-value store de Apify (INPUT), genera el dataset sintético
y escribe los archivos de salida al key-value store. Además:
- Cobra pay-per-event ('users-generated', count=N) por cada usuario generado.
- Siempre escribe un registro OUTPUT con resumen JSON de la corrida.
- Pushea las transacciones al Dataset por defecto (exportable desde Apify UI)
  salvo que push_to_dataset=false.
"""
from __future__ import annotations

import io
from datetime import date, datetime

from apify import Actor

from latam_synth import GeneratorConfig, SyntheticGenerator

# Nombre del evento PPE — debe coincidir con el configurado en Apify Console.
_PPE_EVENT = "users-generated"


def _parse_date(s: str | None, default: date) -> date:
    if not s:
        return default
    return datetime.strptime(s, "%Y-%m-%d").date()


def _to_records(df) -> list[dict]:
    return [
        {k: (v.isoformat() if isinstance(v, date) else v) for k, v in row.items()}
        for row in df.to_dict(orient="records")
    ]


async def main() -> None:
    async with Actor:
        inp = await Actor.get_input() or {}

        users = int(inp.get("users", 1000))
        seed = inp.get("seed")
        countries = inp.get("countries") or None
        fmt = inp.get("format", "csv").lower()
        push_to_dataset = bool(inp.get("push_to_dataset", True))
        start_date = _parse_date(inp.get("start_date"), date(2023, 1, 1))
        end_date = _parse_date(inp.get("end_date"), date(2024, 12, 31))

        if not (1 <= users <= 50_000):
            raise ValueError(f"users debe estar entre 1 y 50,000 (recibido: {users})")

        countries_label = ", ".join(countries) if countries else "todos los países"
        Actor.log.info(
            f"Parámetros recibidos: users={users} | seed={seed} | "
            f"format={fmt} | countries=[{countries_label}] | "
            f"push_to_dataset={push_to_dataset} | "
            f"start_date={start_date} | end_date={end_date}"
        )

        # --- Cobro pay-per-event: se cobra antes de generar para que el
        # usuario vea el cargo aunque cancele, y el límite de gasto se respete.
        charge_result = await Actor.charge(event_name=_PPE_EVENT, count=users)
        Actor.log.info(
            f"PPE: {users} evento(s) '{_PPE_EVENT}' cobrado(s). "
            f"Límite alcanzado: {charge_result.event_charge_limit_reached}"
        )
        if charge_result.event_charge_limit_reached:
            Actor.log.warning(
                "El usuario ha alcanzado su límite de gasto. "
                "El actor se detiene para respetar el presupuesto configurado."
            )
            await Actor.exit(exit_code=0, status_message="Spending limit reached")
            return

        cfg = GeneratorConfig(
            n_users=users,
            seed=seed,
            countries=countries,
            start_date=start_date,
            end_date=end_date,
        )
        data = SyntheticGenerator(cfg).generate()

        store = await Actor.open_key_value_store()
        generated_at = datetime.utcnow().isoformat() + "Z"
        kvs_keys: list[str] = []

        # --- Archivos en el key-value store ---
        if fmt == "json":
            payload = {
                "meta": {
                    "users": len(data["users"]),
                    "goals": len(data["goals"]),
                    "transactions": len(data["transactions"]),
                    "seed": seed,
                    "generated_at": generated_at,
                },
                "users": _to_records(data["users"]),
                "goals": _to_records(data["goals"]),
                "transactions": _to_records(data["transactions"]),
            }
            await store.set_value("OUTPUT_DATA", payload, content_type="application/json")
            kvs_keys.append("OUTPUT_DATA")
        else:
            for table_name, df in data.items():
                buf = io.StringIO()
                df.to_csv(buf, index=False)
                key = f"{table_name}.csv"
                await store.set_value(key, buf.getvalue(), content_type="text/csv")
                kvs_keys.append(key)

        # --- Registro OUTPUT siempre presente (resumen de la corrida) ---
        summary = {
            "parameters": {
                "users": users,
                "seed": seed,
                "format": fmt,
                "countries": countries,
                "push_to_dataset": push_to_dataset,
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
            "rows_generated": {
                "users": len(data["users"]),
                "goals": len(data["goals"]),
                "transactions": len(data["transactions"]),
            },
            "kvs_records": kvs_keys,
            "dataset_pushed": push_to_dataset,
            "generated_at": generated_at,
        }
        await store.set_value("OUTPUT", summary, content_type="application/json")

        # --- Dataset por defecto (exportador nativo de Apify) ---
        if push_to_dataset:
            tx_records = _to_records(data["transactions"])
            chunk = 1000
            for i in range(0, len(tx_records), chunk):
                await Actor.push_data(tx_records[i : i + chunk])
            Actor.log.info(
                f"Dataset: {len(tx_records):,} transacciones pusheadas "
                f"(exportables como JSON/CSV/Excel desde la pestaña Dataset)"
            )

        kvs_list = " | ".join(kvs_keys) + " | OUTPUT"
        Actor.log.info(
            f"✓ Generación completa — {len(data['users']):,} usuarios, "
            f"{len(data['goals']):,} metas, {len(data['transactions']):,} transacciones. "
            f"Key-value store: {kvs_list}"
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
