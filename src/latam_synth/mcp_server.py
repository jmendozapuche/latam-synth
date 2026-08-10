from __future__ import annotations

import json
from typing import Any

import pandas as pd
from mcp.server import MCPServer

from latam_synth import __version__
from latam_synth.engine import GeneratorConfig, SyntheticGenerator


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
        "machine-learning experiments, data pipelines, or agent evaluation."
    ),
    version=__version__,
)


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame into JSON-safe records."""
    return json.loads(
        df.to_json(
            orient="records",
            date_format="iso",
        )
    )


@mcp.tool()
def generate_latam_financial_data(
    users: int = 25,
    seed: int = 42,
    countries: list[str] | None = None,
) -> dict[str, Any]:
    """Generate privacy-safe synthetic financial data for Latin America.

    Args:
        users: Number of synthetic users to generate. Use 1 to 200.
        seed: Random seed for reproducible datasets.
        countries: Optional list of Latin American countries to include,
            for example ["Colombia", "Mexico"].

    Returns:
        Synthetic users, linked savings goals, linked transactions,
        and dataset row counts.
    """
    if users < 1 or users > 200:
        raise ValueError("users must be between 1 and 200.")

    config = GeneratorConfig(
        n_users=users,
        seed=seed,
        countries=countries,
    )

    data = SyntheticGenerator(config).generate()

    users_records = _records(data["users"])
    goals_records = _records(data["goals"])
    transaction_records = _records(data["transactions"])

    return {
        "generator": "LatAm Synth",
        "meta": {
            "users": len(users_records),
            "goals": len(goals_records),
            "transactions": len(transaction_records),
            "seed": seed,
            "countries": countries,
        },
        "users": users_records,
        "goals": goals_records,
        "transactions": transaction_records,
    }


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
