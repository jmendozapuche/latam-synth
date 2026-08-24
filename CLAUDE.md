# CLAUDE.md — Instrucciones para Claude Code

## Qué es este proyecto

Generador de datos sintéticos de comportamiento de ahorro financiero LatAm, calibrado con distribuciones extraídas de un dataset real privado (506,311 registros, app de ahorro, 2015-2024). El producto se vende en marketplaces (Apify primero, luego AWS Marketplace / RapidAPI) sin equipo comercial. El business case completo está en `docs/business_case.md`.

**El activo crítico es `src/latam_synth/calibration_params.json`.** Nunca lo regeneres ni lo modifiques sin instrucción explícita: proviene del dataset fuente que no está en este repo (es privado). Los datos reales NUNCA deben incluirse en el repo ni en el paquete distribuido — solo los parámetros agregados.

## Estado actual (v0.2.0 — distribuido)

Un solo motor, varios adaptadores. **Toda la lógica estadística vive en `SyntheticGenerator`**;
Apify, MCP, la API REST y el paquete LangChain son envoltorios sin lógica propia. No
dupliques generación en un adaptador.

Core (`src/latam_synth/`):

- `engine.py`: users/goals/transactions con integridad referencial, reproducible por seed.
  Mezcla de lognormales para montos + snap a valores redondos + trayectorias temporales por
  meta (proceso de punto con intensidad decreciente) + cópula gaussiana para scores.
- `serialize.py`: conversión a JSON compartida por todos los adaptadores. Contrato único:
  `generator` + `meta` (conteos + parámetros) + las tres tablas, igual que el registro
  `OUTPUT_DATA` del actor. Si un adaptador necesita JSON, usa esto — no lo montes a mano.
- `cli.py`: `latam-synth generate --users 1000 --format csv --out ./output`
- `api.py`: FastAPI, `POST /generate` + `GET /health`. Extra `[api]`.
- `actor.py`: actor de Apify, pay-per-event `users-generated`. Extra `[apify]`.
- `mcp_server.py`: servidor MCP local sobre stdio (`latam-synth-mcp`), ejecuta el generador
  en proceso sin llamar a Apify. Extra `[mcp]`. Detalle en `docs/mcp_local.md`.
- `tests/`: 33 tests pasando (motor + camino MCP).

Validación v0.2 en `docs/validation_report.txt`: KS=0.032 de la mezcla ajustada vs fuente
(el KS del muestreo end-to-end es 0.099 en depósitos, esperado por el reescalado overdue),
60.2% de montos en malla redonda (fuente: 69.5%), 100% de transacciones dentro de
`[created_at, deadline]` y 100% de coherencia achieved/overdue vs `required_amount`.

### Distribución (cuentas del usuario — no publicar sin aprobación)

- Apify Actor: `active_yardstick/latam-synth`
- MCP remoto (hospedado por Apify): `https://mcp.apify.com?tools=active_yardstick/latam-synth`
- MCP Registry: `io.github.jmendozapuche/latam-fintech-synthetic-data` (ver `server.json`)
- Smithery y Glama: listados; Glama arranca el MCP local en contenedor para sus checks
- PyPI: solo el wrapper `langchain-latam-synth` (repo aparte). El core NO está en PyPI.

### Trampa conocida: SDK de MCP

Fijado a `mcp>=2,<3`, verificado con 2.0.0. En 2.x **`mcp.server.fastmcp` no existe**: la
clase es `mcp.server.MCPServer` y los modelos usan snake_case (`tool.input_schema`,
`ToolAnnotations(read_only_hint=...)`, `CallToolResult.is_error`). Casi todos los ejemplos
que circulan son 1.x con FastMCP y fallan al copiarlos.

## Pendientes (en orden de prioridad)

1. **Alinear el contrato del wrapper LangChain.** Devuelve `{run_id, generator, users, goals,
   transactions}` sin `meta`; el MCP local y el actor sí lo devuelven. Alinearlo implica
   publicar `langchain-latam-synth` 0.1.2.
2. **PR a la documentación de LangChain.** Issue `langchain-ai/docs#5420` esperando
   aprobación del maintainer; la página MDX ya está lista en el fork `jmendozapuche/docs`
   (`src/oss/python/integrations/tools/latam_synth.mdx`). No abrir el PR antes de la respuesta.
3. **Build de Glama.** Falló descargando imágenes base de Docker Hub (`context deadline
   exceeded`) — fallo de red del worker, no del servidor MCP. Build step correcto:
   `uv pip install --system -e '.[mcp]' mcp-proxy`; CMD `["mcp-proxy", "--", "latam-synth-mcp"]`.
   Alternativa si reincide: pedirles que usen `Dockerfile.mcp`.
4. **Catálogo MCP de GitHub**: solicitud pendiente.
5. **Decisión abierta**: publicar el core en PyPI para poder declarar un `packages` de tipo
   pypi en `server.json`. Hoy aplazado (duplica versionado por beneficio marginal).

## Convenciones

- Python ≥3.10, type hints, sin dependencias pesadas en el core (numpy+pandas solamente; scipy/sklearn solo en dev/calibración).
- Tests con pytest; cualquier cambio al motor requiere que los 33 tests existentes sigan pasando y añade tests de la nueva funcionalidad.
- Mensajes de commit en español, convencionales (`feat:`, `fix:`, `docs:`).
- La semilla (`seed`) debe garantizar reproducibilidad total — es feature de producto (los compradores de testing la necesitan).

## Qué NO hacer

- No incluir el dataset fuente real (CSV/parquet) en ningún commit.
- No añadir LLMs ni servicios externos al motor de generación — el determinismo estadístico es el producto.
- No publicar a marketplaces sin aprobación humana explícita (las cuentas son del usuario).
