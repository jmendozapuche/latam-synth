# MCP local — despliegue y notas de implementación

El servidor vive en [`src/latam_synth/mcp_server.py`](../src/latam_synth/mcp_server.py).
Ejecuta `SyntheticGenerator` en el mismo proceso: **no llama a Apify ni a ningún
servicio externo**. El camino remoto (MCP hospedado por Apify) es independiente y
está declarado en [`server.json`](../server.json).

## Arranque

```bash
pip install -e ".[mcp]"
latam-synth-mcp                    # entry point (stdio)
python -m latam_synth.mcp_server   # equivalente
```

## Herramientas

| Tool | Args | Anotaciones |
| --- | --- | --- |
| `generate_latam_financial_data` | `users` (1-200), `seed`, `countries`, `start_date`, `end_date` | read-only, idempotent, closed-world |
| `describe_latam_synth_dataset` | — | read-only, idempotent, closed-world |

El payload de `generate_latam_financial_data` usa el mismo contrato que el registro
`OUTPUT_DATA` del actor de Apify — `generator` + `meta` (conteos de filas, seed,
países, ventana temporal, transporte) + las tres tablas — para que un cliente pueda
tratar los tres caminos de forma intercambiable. La serialización está centralizada
en [`serialize.py`](../src/latam_synth/serialize.py); ningún adaptador debe construir
el payload a mano.

Tope de 200 usuarios por llamada (`MAX_USERS`): la respuesta viaja al contexto de un
agente. Para volúmenes grandes, CLI (`latam-synth generate --users 50000`) o actor.

## Versión del SDK MCP

Fijado a `mcp>=2,<3` y verificado contra **mcp 2.0.0**.

Importante para quien venga de ejemplos antiguos: en el SDK 2.x **`mcp.server.fastmcp`
ya no existe**. La clase servidor es `mcp.server.MCPServer` y los modelos usan
snake_case (`tool.input_schema`, `ToolAnnotations(read_only_hint=...)`,
`CallToolResult.is_error`), no el camelCase de la 1.x. Los ejemplos con
`from mcp.server.fastmcp import FastMCP` fallan con `ModuleNotFoundError` en 2.x.

Verificación end-to-end realizada con `mcp.client.stdio` contra el ejecutable:
handshake, `tools/list` (2 herramientas con anotaciones), `tools/call` con datos
reales y error estructurado (`is_error=True`) al pedir 5,000 usuarios.

## Docker

[`Dockerfile.mcp`](../Dockerfile.mcp) empaqueta el servidor sobre `python:3.12-slim`:

```bash
docker build -f Dockerfile.mcp -t latam-synth-mcp .
docker run -i --rm latam-synth-mcp
```

Se ejecuta con `-i` y sin TTY: stdio es el transporte.

## Glama

Configuración de build/run para el worker de Glama:

```json
{
  "build": ["uv pip install --system -e '.[mcp]' mcp-proxy"],
  "cmd": ["mcp-proxy", "--", "latam-synth-mcp"]
}
```

`mcp-proxy` debe instalarse **en el mismo paso de build** (el worker no lo trae de
serie); ese fue el único ajuste respecto a la configuración inicial.

Estado conocido: el build de Glama falló descargando las imágenes base de Docker Hub
(`context deadline exceeded`, tanto con `debian:trixie-slim` como con
`debian:bookworm-slim`). Es un fallo de red del worker, **no** del servidor MCP: la
verificación stdio local pasa. Si vuelve a ocurrir, la alternativa es pedirles que
usen `Dockerfile.mcp` directamente.

## Tests

[`tests/test_mcp_server.py`](../tests/test_mcp_server.py) cubre registro de
herramientas, esquema de argumentos, rangos inválidos, fechas inválidas,
serializabilidad JSON, integridad referencial y reproducibilidad por seed. Se salta
solo si el extra `[mcp]` no está instalado (`pytest.importorskip`).
