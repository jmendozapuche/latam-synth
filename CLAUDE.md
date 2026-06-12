# CLAUDE.md — Instrucciones para Claude Code

## Qué es este proyecto

Generador de datos sintéticos de comportamiento de ahorro financiero LatAm, calibrado con distribuciones extraídas de un dataset real privado (506,311 registros, app de ahorro, 2015-2024). El producto se vende en marketplaces (Apify primero, luego AWS Marketplace / RapidAPI) sin equipo comercial. El business case completo está en `docs/business_case.md`.

**El activo crítico es `src/latam_synth/calibration_params.json`.** Nunca lo regeneres ni lo modifiques sin instrucción explícita: proviene del dataset fuente que no está en este repo (es privado). Los datos reales NUNCA deben incluirse en el repo ni en el paquete distribuido — solo los parámetros agregados.

## Estado actual (v0.1 — funcional)

- `engine.py`: genera users/goals/transactions con integridad referencial, reproducible por seed. Lognormales simples + muestreo categórico directo + cópula gaussiana para scores correlacionados.
- `cli.py`: `latam-synth generate --users 1000 --format csv --out ./output`
- `tests/`: 6 tests pasando (integridad, reproducibilidad, calibración de proporciones).
- Validación v0.1 en `docs/validation_report.txt`: KS=0.068 en log-montos. Cuerpo central fiel (desvío 7-10% en p25-p90), **cola alta desviada 35-45% en p95-p99** — ese es el principal trabajo de v0.2.

## Tareas v0.2 (en orden de prioridad)

1. **Mezcla de lognormales para montos.** La distribución real es multimodal: micro-depósitos (~$4-20), depósitos típicos (~$100-800) y depósitos grandes (>$6,000). Ajustar mezcla de 2-3 componentes (sklearn GaussianMixture sobre log-montos, o EM manual para no añadir dependencia pesada). Objetivo: KS < 0.03 y desvío p99 < 15%. Los parámetros de la mezcla se añaden a calibration_params.json bajo una clave nueva `amount_mixture` SIN tocar las claves existentes — para eso sí necesitas el CSV fuente; pídelo al usuario, ajusta, y elimina el CSV del workspace al terminar.
2. **Snap a montos redondos.** En los datos reales los depósitos se concentran en valores redondos ($50, $100, $500, $1,000). Post-procesar ~60-70% de los montos generados con snap al valor redondo más cercano (calibrar la proporción exacta contra fuente).
3. **Trayectorias temporales coherentes por meta.** Hoy las fechas de transacción son independientes de la meta. Deben caer entre `created_at` y `deadline` de su meta, con frecuencia decreciente (el abandono real: 73.8% overdue). Modelar como proceso de punto con intensidad decreciente; las metas `achieved` deben acumular ≥ required_amount, las `overdue` deben quedarse cortas.
4. **API FastAPI** (`api.py`): endpoint POST /generate con los mismos parámetros del CLI, respuesta JSON o link a archivo. Incluir rate limiting básico y endpoint GET /health.
5. **Actor de Apify**: empaquetar según https://docs.apify.com/platform/actors — Dockerfile, `.actor/actor.json`, input schema JSON (users, seed, countries, format), output al key-value store. El listing usa `docs/listing_apify.md` (crearlo: título, descripción, casos de uso, pricing sugerido en business case sección 6).
6. **Ficha de privacidad** (`docs/privacy.md`): documento corto explicando que el output es 100% sintético, generado de distribuciones agregadas, sin derivación de registros individuales, sin PII. Es material de venta, escribirlo orientado a un comprador técnico que debe justificar la compra ante compliance.

## Convenciones

- Python ≥3.10, type hints, sin dependencias pesadas en el core (numpy+pandas solamente; scipy/sklearn solo en dev/calibración).
- Tests con pytest; cualquier cambio al motor requiere que los 6 tests existentes sigan pasando y añade tests de la nueva funcionalidad.
- Mensajes de commit en español, convencionales (`feat:`, `fix:`, `docs:`).
- La semilla (`seed`) debe garantizar reproducibilidad total — es feature de producto (los compradores de testing la necesitan).

## Qué NO hacer

- No incluir el dataset fuente real (CSV/parquet) en ningún commit.
- No añadir LLMs ni servicios externos al motor de generación — el determinismo estadístico es el producto.
- No publicar a marketplaces sin aprobación humana explícita (las cuentas son del usuario).
