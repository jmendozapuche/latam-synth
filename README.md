# latam-synth

Generador de datos sintéticos de comportamiento de ahorro financiero, calibrado con las distribuciones estadísticas de 506,311 registros reales de una app de ahorro LatAm (2015-2024): 305,808 transacciones, 108,570 metas de ahorro y 91,933 usuarios de México, Colombia, Argentina, Perú, Chile y más.

**El output es 100% sintético**: ningún registro deriva de un usuario real, solo de distribuciones agregadas. Sin PII, sin riesgo de reidentificación.

## Para qué sirve

- **Testing y QA fintech**: fixtures realistas para pipelines de pago, apps de presupuesto, motores de metas.
- **Demos y POCs**: dashboards con datos verosímiles de LatAm que se pueden mostrar públicamente.
- **Entrenamiento de ML**: datos de arranque para modelos de churn, recomendación y segmentación con patrones reales (estacionalidad, tasas de abandono, categorías de metas).
- **Educación**: datasets ilimitados para cursos de data science con narrativa de negocio real.

## Uso rápido

```bash
pip install -e .
latam-synth generate --users 5000 --seed 42 --format csv --out ./output
# Solo México y Colombia, formato parquet:
latam-synth generate --users 10000 --countries Mexico Colombia --format parquet
```

```python
from latam_synth import SyntheticGenerator, GeneratorConfig
data = SyntheticGenerator(GeneratorConfig(n_users=1000, seed=42)).generate()
data["transactions"].head()
```

## Qué hace fiel a este generador

Calibración verificada contra datos reales (ver `docs/validation_report.txt`): distribuciones de montos lognormales por tipo de transacción, estacionalidad mensual real (pico de enero post-propósitos, valle de diciembre), 8 categorías de metas con montos y horizontes propios, tasas de logro/abandono reales (73.8% de metas vencidas), uplift de metas compartidas, y scores de usuario correlacionados (cópula gaussiana, ρ=0.89 disciplina-logro).

## API REST

```bash
pip install -e ".[api]"
uvicorn latam_synth.api:app --port 8000
```

```bash
# JSON con las tres tablas (users, goals, transactions)
curl -s -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"users": 100, "seed": 42, "countries": ["Mexico", "Colombia"]}' | jq .meta
# {"users": 100, "goals": 121, "transactions": 453}

# CSV de transacciones directamente
curl -s -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "Accept: text/csv" \
  -d '{"users": 500, "seed": 7}' -o transactions.csv

# Health check
curl http://localhost:8000/health
# {"status": "ok", "version": "0.2.0"}
```

Rate limit: 10 requests/min por IP. Máximo 50,000 usuarios por request.

## Desarrollo

```bash
pip install -e ".[dev]"
pytest
```

Changelog: v0.2 añade mezcla de lognormales (KS=0.032), snap a valores redondos (69.5% en malla), trayectorias temporales coherentes por meta (100% tx en ventana [created_at, deadline]), API FastAPI y actor Apify.
