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

Output is 100% synthetic — no record derives from a real individual. No PII, no re-identification risk. GDPR / LGPD / CCPA / LFPDPPP non-applicable.

<details>
<summary><strong>Ficha Técnica de Privacidad completa (haz clic para expandir)</strong></summary>

**Versión:** 0.2.0 · **Fecha:** 2026-06-12 · **Clasificación:** Pública

---

### 1. Naturaleza del output

LatAm Synth produce **datos 100% sintéticos**. Ningún registro del archivo de salida corresponde a, ni puede ser revertido a, un individuo real. El output es un conjunto de datos estadísticamente plausible generado por un modelo probabilístico; no es un subconjunto, anonimización ni seudonimización de datos reales.

---

### 2. Ausencia de PII y riesgo de re-identificación

El output no contiene:

| Campo | Presente en output | Nota |
|---|---|---|
| Nombre, apellido | No | Sustituido por ID UUID aleatorio |
| Email, teléfono | No | No se genera |
| Dirección, ubicación GPS | No | Solo país, de distribución agregada |
| Fecha de nacimiento | No | No se genera |
| Número de documento | No | No se genera |
| Información financiera real | No | Montos son sintéticos del modelo |
| IP, device ID | No | No se genera |

El campo `user_id` es un UUID v4 generado en tiempo de ejecución. No existe una tabla de correspondencia con personas reales porque esa tabla no existe: los usuarios sintéticos no tienen contrapartes reales.

El riesgo de re-identificación es **nulo** por construcción: el modelo no dispone de información individual en ninguna etapa del pipeline.

---

### 3. Metodología de calibración: qué se usó y qué no

**Dataset fuente:** La calibración se realizó sobre un dataset privado de **506,311 registros** de transacciones de una aplicación de ahorro LatAm (2015-2024). Este dataset nunca se distribuye con el producto, no se almacena en el entorno de producción, y se usó exclusivamente como fuente estadística en un proceso offline descartado tras la extracción de parámetros.

**Qué se extrajo:** únicamente estadísticas agregadas — percentiles de distribución de montos, parámetros de mezcla de lognormales, proporciones categóricas, correlaciones de cohorte y estacionalidad. **Ningún registro individual** del dataset fuente está codificado, implícito ni recuperable a partir de estos parámetros.

**Garantía matemática:** Las distribuciones paramétricas y los procesos de punto son modelos de la *forma* de los datos, no memorias de los datos. La capacidad de recuperar registros individuales a partir de los parámetros es matemáticamente equivalente a recuperarlos desde los momentos de una distribución — imposible en ausencia del dataset original.

---

### 4. Proceso de generación

```
calibration_params.json  (parámetros agregados)
         │
         ▼
  SyntheticGenerator(seed)
         │
         ├─ Usuarios: cópula gaussiana sobre distribuciones marginales
         ├─ Metas: muestreo de categorías, montos y horizontes calibrados
         └─ Transacciones: proceso de punto con intensidad decreciente,
            montos de mezcla de lognormales + snap a valores redondos
         │
         ▼
  Output: users.csv, goals.csv, transactions.csv
```

El proceso es **determinista dado un seed**: el mismo seed produce el mismo output byte a byte.

---

### 5. Marco regulatorio aplicable

| Regulación | Aplica al output | Fundamento |
|---|---|---|
| GDPR (UE) | **No aplica** | El output no contiene datos de personas físicas identificadas o identificables (Art. 4.1 GDPR) |
| LGPD (Brasil) | **No aplica** | Sin dados pessoais (Art. 5.I LGPD) |
| CCPA (California) | **No aplica** | Sin "personal information" de consumidores de California |
| LFPDPPP (México) | **No aplica** | Sin datos personales (Art. 3.V LFPDPPP) |
| LOPD (España/Colombia) | **No aplica** | Sin datos de personas físicas identificadas |

---

### 6. Recomendaciones para el área de Compliance del comprador

1. **No se requiere DPA:** LatAm Synth no procesa datos personales del comprador ni de terceros.
2. **No se requiere consentimiento de usuarios finales:** los datos de salida no corresponden a personas reales; no hay sujetos de datos cuyos derechos ARCO/ARCOPLUS gestionar.
3. **Uso recomendado:** desarrollo y prueba de modelos de ML, benchmarking de sistemas financieros, datos de demostración para pre-producción, investigación académica.
4. **Uso no recomendado:** no debe usarse como sustituto de datos reales en decisiones financieras individuales (scoring crediticio, underwriting) sin validación adicional.
5. **Auditoría:** los parámetros de calibración son públicamente inspeccionables. Cualquier auditor técnico puede verificar que el pipeline no contiene rutas de acceso a datos reales.

</details>
