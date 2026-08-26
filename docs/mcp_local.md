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

El worker de Glama clona el repo, construye una imagen y arranca el servidor MCP
detras de `mcp-proxy`. Configuracion que funciona:

```json
{
  "build": [
    "uv venv /opt/venv --python 3.12",
    "uv pip install --python /opt/venv/bin/python -e '.[mcp]'"
  ],
  "cmd": ["mcp-proxy", "--", "/opt/venv/bin/latam-synth-mcp"]
}
```

Dos cosas que hay que respetar, aprendidas a golpes:

**No usar `--system`.** La imagen base de Glama instala Node 24, que arrastra el
Python 3.13 de Debian a `/usr`. Debian lo marca como *externally managed* (PEP 668)
y `uv pip install --system` falla ahi con `exit code 2` sin llegar a instalar nada
nuestro. La imagen tambien instala un Python 3.12 propio via uv, que no tiene esa
restriccion, pero `--system` no lo elige. De ahi el venv explicito en `/opt/venv`.
Alternativa de una linea si solo se admite un paso:
`uv pip install --system --break-system-packages -e '.[mcp]'`.

**Ruta absoluta en el CMD.** Los ejecutables de `/opt/venv` no estan en el PATH del
contenedor, asi que `latam-synth-mcp` a secas no se encuentra.

**No instalar `mcp-proxy`.** La imagen base ya lo trae (`npm install -g
mcp-proxy@6.4.3`); anadirlo al build es redundante.

Historico: el primer intento ni siquiera llego a construir — el worker fallaba
descargando las imagenes base de Docker Hub (`context deadline exceeded`, con
`debian:trixie-slim` y `debian:bookworm-slim`). Ese problema desaparecio solo. Si
vuelve a aparecer, la alternativa es pedirles que usen `Dockerfile.mcp`.

## Tests

[`tests/test_mcp_server.py`](../tests/test_mcp_server.py) cubre registro de
herramientas, esquema de argumentos, rangos inválidos, fechas inválidas,
serializabilidad JSON, integridad referencial y reproducibilidad por seed. Se salta
solo si el extra `[mcp]` no está instalado (`pytest.importorskip`).
