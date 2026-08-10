# latam-synth

**Privacy-safe synthetic financial data for Latin American fintech — available through Python, CLI, REST, Apify Actor, and Model Context Protocol (MCP) for AI agents.**

Generador de datos sintéticos de comportamiento de ahorro financiero, calibrado con las distribuciones estadísticas de **506,311 registros reales** de una app de ahorro LatAm (2015–2024): 305,808 transacciones, 108,570 metas de ahorro y 91,933 usuarios de México, Colombia, Argentina, Perú, Chile y más.

**El output es 100% sintético**: ningún registro deriva de un usuario real, solo de distribuciones agregadas. Sin PII y sin riesgo de reidentificación.

---

## Model Context Protocol (MCP)

LatAm Synth is available to AI agents as an **MCP tool** through the hosted **Apify MCP Server**.

This repository contains the synthetic data generator and the Apify Actor implementation. The MCP transport server itself is provided by Apify, which exposes the `active_yardstick/latam-synth` Actor as a callable MCP tool.

### MCP details

- **MCP capability:** Tools
- **Transport:** Streamable HTTP
- **Hosted MCP server:** Apify MCP Server
- **Actor exposed as tool:** `active_yardstick/latam-synth`
- **Authentication:** Apify OAuth or Bearer token
- **Official MCP Registry name:** `io.github.jmendozapuche/latam-fintech-synthetic-data`
- **Registry metadata:** [`server.json`](./server.json)
- **Apify Actor:** https://apify.com/active_yardstick/latam-synth

### MCP endpoint

```text
https://mcp.apify.com?tools=active_yardstick/latam-synth
```

The `tools` parameter restricts the Apify MCP Server to the LatAm Synth Actor, making it directly discoverable and callable by compatible AI agents.

### Example MCP configuration — OAuth

```json
{
  "mcpServers": {
    "latam-synth": {
      "url": "https://mcp.apify.com?tools=active_yardstick/latam-synth"
    }
  }
}
```

On first connection, a compatible MCP client can open the Apify OAuth flow so the user can authorize access without placing an API token directly in the configuration.

### Example MCP configuration — Bearer token

```json
{
  "mcpServers": {
    "latam-synth": {
      "url": "https://mcp.apify.com?tools=active_yardstick/latam-synth",
      "headers": {
        "Authorization": "Bearer <APIFY_TOKEN>"
      }
    }
  }
}
```

Replace `<APIFY_TOKEN>` with an Apify API token.

### What AI agents can do with LatAm Synth

An MCP-compatible agent can invoke LatAm Synth to generate:

- synthetic financial users
- linked savings goals
- deposit and withdrawal transactions
- country-filtered Latin American datasets
- reproducible datasets using a random seed
- realistic fintech test data without exposing personally identifiable information

Typical agent use cases include:

- evaluating financial AI agents
- generating test fixtures on demand
- creating synthetic datasets for demos and POCs
- testing recommendation or savings assistants
- bootstrapping ML and data-pipeline experiments

LatAm Synth currently exposes its functionality through **MCP Tools**. It does not currently expose MCP Resources or Prompts.

### How MCP is implemented

LatAm Synth does **not** need to implement an MCP transport server inside this Python repository.

The architecture is:

```text
MCP-compatible AI client
        |
        |  Streamable HTTP
        v
Apify MCP Server
        |
        |  exposes Actor as MCP Tool
        v
active_yardstick/latam-synth
        |
        v
Synthetic users + goals + transactions
```

Apify provides the hosted MCP server and authentication layer. The LatAm Synth Actor provides the executable tool functionality and structured input/output.

---

## Para qué sirve

- **Testing y QA fintech**: fixtures realistas para pipelines de pago, apps de presupuesto y motores de metas.
- **Demos y POCs**: dashboards con datos verosímiles de LatAm que se pueden mostrar públicamente.
- **Entrenamiento de ML**: datos de arranque para modelos de churn, recomendación y segmentación con patrones reales como estacionalidad, tasas de abandono y categorías de metas.
- **AI agents**: generación bajo demanda de datasets financieros sintéticos a través de MCP.
- **Educación**: datasets ilimitados para cursos de data science con narrativa de negocio real.

---

## Uso rápido

### CLI

```bash
pip install -e .
latam-synth generate --users 5000 --seed 42 --format csv --out ./output
```

Solo México y Colombia, formato parquet:

```bash
latam-synth generate --users 10000 --countries Mexico Colombia --format parquet
```

### Python

```python
from latam_synth import SyntheticGenerator, GeneratorConfig

data = SyntheticGenerator(
    GeneratorConfig(n_users=1000, seed=42)
).generate()

data["transactions"].head()
```

---

## Qué hace fiel a este generador

La calibración fue verificada contra datos reales. Ver:

```text
docs/validation_report.txt
```

El generador incorpora:

- distribuciones de montos lognormales por tipo de transacción
- estacionalidad mensual real
- pico de enero post-propósitos y valle de diciembre
- 8 categorías de metas con montos y horizontes propios
- tasas de logro y abandono observadas
- 73.8% de metas vencidas
- uplift de metas compartidas
- scores de usuario correlacionados
- cópula gaussiana con ρ=0.89 para disciplina-logro
- trayectorias temporales coherentes por meta
- integridad referencial entre usuarios, metas y transacciones

---

## Apify Actor

LatAm Synth is also available as a hosted Apify Actor:

```text
active_yardstick/latam-synth
```

Actor page:

```text
https://apify.com/active_yardstick/latam-synth
```

The Actor can be called directly from Apify, through the Apify API, or exposed to AI clients through the Apify MCP Server.

Example input:

```json
{
  "users": 1000,
  "seed": 42,
  "countries": ["Mexico", "Colombia"],
  "format": "csv",
  "push_to_dataset": true,
  "start_date": "2023-01-01",
  "end_date": "2024-12-31"
}
```

The `seed` parameter makes generation reproducible. The same seed and configuration produce the same synthetic output.

---

## Where to find your output (Apify)

Every run writes output to two places.

### Key-value store — all three tables

1. Open the run in Apify Console and click the **Storage** tab.
2. Click **Key-value store**.
3. Download the generated files:
   - `users.csv` — one row per synthetic user
   - `goals.csv` — savings goals linked to users
   - `transactions.csv` — deposit/withdrawal transactions linked to goals
   - `OUTPUT` — always present; JSON summary of the run, including parameters, row counts and downloadable keys
   - if `format: json` was selected, `OUTPUT_DATA` contains all three tables in a single JSON file instead of the three CSV files
4. Click the download icon next to each key to save the file.

### Dataset — transactions

By default (`push_to_dataset: true`), all transactions are also pushed to the run's **Dataset**.

This allows you to:

- export as JSON, CSV, or Excel directly from the Dataset tab
- connect native Apify integrations to the Dataset output
- consume transactions programmatically

To disable this for very large runs where only the key-value-store files are needed, set:

```json
{
  "push_to_dataset": false
}
```

The run log prints exact file names and row counts at the end of execution.

---

## API REST local

Install the API dependencies:

```bash
pip install -e ".[api]"
uvicorn latam_synth.api:app --port 8000
```

Generate JSON with the three tables:

```bash
curl -s -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"users": 100, "seed": 42, "countries": ["Mexico", "Colombia"]}' | jq .meta
```

Example metadata response:

```json
{
  "users": 100,
  "goals": 121,
  "transactions": 453
}
```

Download transaction CSV directly:

```bash
curl -s -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "Accept: text/csv" \
  -d '{"users": 500, "seed": 7}' \
  -o transactions.csv
```

Health check:

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "version": "0.2.0"
}
```

Local REST API limits:

- Rate limit: 10 requests/min per IP
- Maximum: 50,000 users per request

---

## Privacy

The generated datasets are designed for development, testing, demos, experimentation and education without requiring production PII.

Key properties:

- 100% synthetic records
- no row is copied from a real user
- no names, emails, IDs or other direct PII are reproduced from the calibration dataset
- generation is based on aggregate statistical distributions
- synthetic tables preserve realistic relationships between users, goals and transactions

---

## Desarrollo

```bash
pip install -e ".[dev]"
pytest
```

---

## MCP registry metadata

This repository includes [`server.json`](./server.json) for MCP registry discovery.

Current server identity:

```text
io.github.jmendozapuche/latam-fintech-synthetic-data
```

The registered remote MCP endpoint is:

```text
https://mcp.apify.com?tools=active_yardstick/latam-synth
```

---

## Changelog

### v0.2

- mezcla de lognormales (KS=0.032)
- snap a valores redondos (69.5% en malla)
- trayectorias temporales coherentes por meta
- 100% de transacciones dentro de la ventana `[created_at, deadline]`
- API FastAPI
- Apify Actor
- MCP exposure through the hosted Apify MCP Server
