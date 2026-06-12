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

## Desarrollo

```bash
pip install -e ".[dev]"
pytest
```

Roadmap v0.2 en `CLAUDE.md` (mezcla de lognormales para la cola alta, trayectorias temporales coherentes, API, actor de Apify).
