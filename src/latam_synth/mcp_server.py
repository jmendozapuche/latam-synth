"""Servidor MCP local (transporte stdio) sobre el generador.

Este camino NO llama a Apify: instancia `SyntheticGenerator` en el mismo proceso.
Es el complemento del MCP remoto hospedado por Apify (declarado en `server.json`)
y está pensado para clientes MCP locales (Claude Desktop, Claude Code, MCP
Inspector) y para los checks automáticos de catálogos como Glama, que arrancan el
servidor en un contenedor y listan/ejecutan sus herramientas.

Arranque:
    latam-synth-mcp          # entry point declarado en pyproject.toml
    python -m latam_synth.mcp_server

Instalación del extra:
    pip install "latam-synth[mcp]"

Nota de versión: fijado a mcp>=2,<3. En el SDK 2.x `mcp.server.fastmcp` ya no
existe — la clase es `mcp.server.MCPServer` y los modelos usan snake_case
(`tool.input_schema`, `ToolAnnotations(read_only_hint=...)`, `result.is_error`).
"""
from __future__ import annotations

from datetime import date
from typing import Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from latam_synth import __version__
from latam_synth.engine import GeneratorConfig, SyntheticGenerator, load_params
from latam_synth.serialize import dataset_payload

# Tope de usuarios por llamada. El generador local escala a decenas de miles, pero
# la respuesta viaja al contexto de un agente: 200 usuarios ya son ~700 filas de
# transacciones. Para volúmenes grandes se usa el CLI o el actor de Apify.
MAX_USERS = 200

_DEFAULT_START = date(2023, 1, 1)
_DEFAULT_END = date(2024, 12, 31)

# Las dos herramientas son puras: no escriben nada, no consultan servicios
# externos y el mismo seed devuelve el mismo dataset.
_PURE = ToolAnnotations(
    read_only_hint=True,
    idempotent_hint=True,
    open_world_hint=False,
)

mcp = MCPServer(
    name="latam-fintech-synthetic-data",
    title="LatAm Fintech Synthetic Data",
    description=(
        "Generate realistic, privacy-safe synthetic financial users, "
        "savings goals, and transactions for Latin American fintech."
    ),
    instructions=(
        "Use generate_latam_financial_data when an AI agent needs "
        "synthetic Latin American financial data for testing, QA, demos, "
        "machine-learning experiments, data pipelines, or agent evaluation. "
        "Use describe_latam_synth_dataset when you only need the schema, "
        "the available countries or the goal categories."
    ),
    version=__version__,
)


def _parse_date(value: str | None, default: date) -> date:
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError as exc:  # mensaje accionable para el agente
        raise ValueError(
            f"Invalid date {value!r}. Use ISO format, for example 2024-01-31."
        ) from exc


@mcp.tool(annotations=_PURE)
def generate_latam_financial_data(
    users: int = 25,
    seed: int = 42,
    countries: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Generate privacy-safe synthetic financial data for Latin America.

    Use this tool when you need synthetic financial users, savings goals and
    transactions for Latin American fintech testing, QA, demos,
    machine-learning experiments, data pipelines or agent evaluation. The output
    is fully synthetic: it is sampled from aggregate distributions and contains
    no personally identifiable information and no real records.

    Args:
        users: Number of synthetic users to generate. Use 1 to 200.
        seed: Random seed for reproducible datasets. The same seed and
            parameters always return the same dataset.
        countries: Optional list of Latin American countries to include,
            for example ["Colombia", "Mexico"].
        start_date: Optional ISO start date of the generated period,
            for example "2023-01-01".
        end_date: Optional ISO end date of the generated period,
            for example "2024-12-31".

    Returns:
        Synthetic users, linked savings goals, linked transactions,
        and dataset row counts.
    """
    if not isinstance(users, int) or isinstance(users, bool):
        raise ValueError("users must be an integer.")
    if users < 1 or users > MAX_USERS:
        raise ValueError(
            f"users must be between 1 and {MAX_USERS}. For larger volumes use "
            "the latam-synth CLI or the Apify Actor."
        )

    start = _parse_date(start_date, _DEFAULT_START)
    end = _parse_date(end_date, _DEFAULT_END)
    if end <= start:
        raise ValueError("end_date must be later than start_date.")

    config = GeneratorConfig(
        n_users=users,
        seed=seed,
        countries=countries or None,
        start_date=start,
        end_date=end,
    )
    data = SyntheticGenerator(config).generate()

    return dataset_payload(
        data,
        meta={
            "seed": seed,
            "countries": countries or None,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "version": __version__,
            "transport": "mcp-local",
        },
    )


@mcp.tool(annotations=_PURE)
def describe_latam_synth_dataset() -> dict[str, Any]:
    """Describe the schema and calibration of the LatAm Synth dataset.

    Use this tool to inspect which tables, columns, goal categories and
    countries are available before generating data. It performs no generation
    and takes no arguments.

    Returns:
        Table columns, relationships, goal categories, available countries
        and the privacy policy of the generated data.
    """
    params = load_params()
    return {
        "generator": "LatAm Synth",
        "version": __version__,
        "tables": {
            "users": [
                "user_id",
                "country",
                "gamification_score",
                "savings_discipline_score",
                "goals_completed_ratio",
            ],
            "goals": [
                "goal_id",
                "user_id",
                "category",
                "name",
                "required_amount",
                "created_at",
                "deadline",
                "goal_status",
                "is_shared",
            ],
            "transactions": [
                "transaction_id",
                "goal_id",
                "user_id",
                "date",
                "transaction_type",
                "amount",
            ],
        },
        "relationships": [
            "goals.user_id -> users.user_id",
            "transactions.goal_id -> goals.goal_id",
            "transactions.user_id -> users.user_id",
        ],
        "goal_categories": sorted(params["goals"]["categories"].keys()),
        "countries": sorted(params["users"]["geo_mix"].keys()),
        "goal_statuses": ["achieved", "overdue", "in_progress"],
        "transaction_types": ["deposit", "withdrawal"],
        "max_users_per_call": MAX_USERS,
        "privacy": (
            "Synthetic output sampled from aggregate distributions. No real "
            "records, no PII, reproducible by seed."
        ),
    }


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
