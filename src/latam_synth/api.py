"""API REST para latam-synth.

Endpoints:
  GET  /health          — liveness check
  POST /generate        — genera dataset sintético

Formato de respuesta controlado por el header Accept:
  application/json  → JSON con las tres tablas
  text/csv          → CSV de transacciones (tabla principal de uso comercial)

Instalar dependencias: pip install "latam-synth[api]"
Arrancar: uvicorn latam_synth.api:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import io
import time
from datetime import date
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from latam_synth import GeneratorConfig, SyntheticGenerator

app = FastAPI(
    title="LatAm Synth API",
    description="Generador de datos sintéticos de comportamiento de ahorro financiero LatAm.",
    version="0.2.0",
)

# ---------- rate limiting simple en memoria ----------
# Límite: 10 requests de /generate por minuto por IP.
_RATE_WINDOW = 60        # segundos
_RATE_LIMIT = 10         # requests por ventana
_rate_counters: dict[str, list[float]] = {}


def _check_rate(ip: str) -> None:
    now = time.time()
    window = _rate_counters.setdefault(ip, [])
    _rate_counters[ip] = [t for t in window if now - t < _RATE_WINDOW]
    if len(_rate_counters[ip]) >= _RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: máximo {_RATE_LIMIT} requests/minuto por IP.",
        )
    _rate_counters[ip].append(now)


# ---------- modelos ----------

class GenerateRequest(BaseModel):
    users: int = Field(1000, ge=1, le=50_000, description="Número de usuarios a generar.")
    seed: Optional[int] = Field(None, description="Semilla para reproducibilidad total.")
    countries: Optional[list[str]] = Field(
        None, description="Lista de países (None = mezcla calibrada completa)."
    )
    format: str = Field(
        "json",
        pattern="^(json|csv)$",
        description="Formato de respuesta: 'json' o 'csv'. También controlable via Accept.",
    )
    start_date: date = Field(date(2023, 1, 1), description="Inicio del período de generación.")
    end_date: date = Field(date(2024, 12, 31), description="Fin del período de generación.")
    goals_per_user_lambda: float = Field(1.2, gt=0, description="Lambda Poisson de metas por usuario.")
    tx_per_goal_lambda: float = Field(2.8, gt=0, description="Lambda Poisson de transacciones por meta.")

    model_config = {"json_schema_extra": {"example": {
        "users": 500, "seed": 42, "countries": ["Mexico", "Colombia"], "format": "json",
    }}}


# ---------- endpoints ----------

@app.get("/health", summary="Liveness check")
def health() -> dict:
    return {"status": "ok", "version": "0.2.0"}


@app.post("/generate", summary="Genera dataset sintético LatAm")
def generate(
    req: GenerateRequest,
    request: Request,
    accept: str = Header(default="application/json"),
) -> Response:
    ip = request.client.host if request.client else "unknown"
    _check_rate(ip)

    cfg = GeneratorConfig(
        n_users=req.users,
        seed=req.seed,
        countries=req.countries,
        start_date=req.start_date,
        end_date=req.end_date,
        goals_per_user_lambda=req.goals_per_user_lambda,
        tx_per_goal_lambda=req.tx_per_goal_lambda,
    )
    data = SyntheticGenerator(cfg).generate()

    want_csv = "text/csv" in accept or req.format == "csv"

    if want_csv:
        buf = io.StringIO()
        data["transactions"].to_csv(buf, index=False)
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=transactions.csv"},
        )

    # JSON: serializar fechas como strings
    def _to_records(df):
        return [
            {k: (v.isoformat() if isinstance(v, date) else v) for k, v in row.items()}
            for row in df.to_dict(orient="records")
        ]

    return JSONResponse({
        "meta": {
            "users": len(data["users"]),
            "goals": len(data["goals"]),
            "transactions": len(data["transactions"]),
            "seed": req.seed,
        },
        "users": _to_records(data["users"]),
        "goals": _to_records(data["goals"]),
        "transactions": _to_records(data["transactions"]),
    })
