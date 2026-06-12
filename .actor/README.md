# LatAm Synth — Synthetic Financial Savings Data Generator

Generate realistic synthetic datasets of financial saving behavior for Latin America, calibrated on 506,311 real records (2015–2024). Outputs users, savings goals, and transactions with full referential integrity, 100% synthetic, zero PII.

## What you get

Each run produces three linked tables:

| Table | Description |
|---|---|
| `users` | Synthetic users with country, scores, join date |
| `goals` | Savings goals with category, required amount, status (achieved / overdue / in_progress) |
| `transactions` | Deposits and withdrawals within each goal's window |

**Calibrated against real data:** lognormal mixture distributions (KS=0.032), 69.5% round-value snap, 73.8% overdue rate, monthly seasonality, 8 goal categories with realistic amounts and horizons.

## Pricing — Pay Per Event

This actor uses Apify's **Pay Per Event** model. You are charged per **synthetic user generated**, regardless of output format or destination.

| Event | Unit | What triggers it |
|---|---|---|
| `users-generated` | per user | Each run, before data is written |

**Example:** generating 1,000 users = 1,000 × unit price.

The charge fires before output is written, so it applies equally whether you use CSV files, JSON, or the Dataset export — there is no cheaper path. If your spending limit is reached mid-run, the actor stops cleanly and reports the limit in the log.

Set your spending cap in **Apify Console → Run → Max total charge** before starting a run.

## Input parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `users` | integer | 1000 | Number of synthetic users (1–50,000) |
| `seed` | integer | null | Random seed for reproducibility. Same seed → identical output |
| `countries` | string[] | null | Restrict to specific countries. Empty = full LatAm mix (Mexico 46.6%, Colombia 14.4%, …) |
| `format` | csv \| json | csv | Output format for Key-value store files |
| `push_to_dataset` | boolean | true | Push transactions to Apify Dataset (enables native JSON/CSV/Excel export and integrations) |
| `start_date` | string | 2023-01-01 | Start of generation period (YYYY-MM-DD) |
| `end_date` | string | 2024-12-31 | End of generation period (YYYY-MM-DD) |

## Where to find your output

Every run writes to **two places**:

### Key-value store — all three tables

1. Open the run → **Storage** tab → **Key-value store**
2. Download files:
   - `users.csv` / `goals.csv` / `transactions.csv` (CSV mode)
   - `OUTPUT_DATA` — single JSON with all three tables (JSON mode)
   - `OUTPUT` — always present; JSON summary of the run (parameters, row counts, file list)

### Dataset — transactions (Apify-native export)

When `push_to_dataset=true` (default), all transactions appear in the run's **Dataset** tab:

- Export as **JSON, CSV, or Excel** in one click
- Connect **Google Sheets**, webhooks, or any Apify integration
- Disable with `push_to_dataset=false` for runs > 10K users where you only need the KVS files

## Use cases

- **Fintech testing & QA** — realistic fixtures for payment pipelines, budget apps, savings engines
- **ML training data** — bootstrap churn, recommendation, and segmentation models with real LatAm patterns
- **Demos & POCs** — dashboards with publicly shareable synthetic data
- **Education** — unlimited datasets for data science courses with real business narrative

## Privacy & compliance

Output is 100% synthetic — no record derives from a real individual. No PII, no re-identification risk. GDPR / LGPD / CCPA / LFPDPPP non-applicable. Full technical privacy documentation: see `docs/privacy.md` in the [GitHub repository](https://github.com/jmendozapuche/latam-synth).
