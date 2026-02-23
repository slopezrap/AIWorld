# MCP (Model Context Protocol) en AIFoundry

## Visión General

AIFoundry soporta MCPs externos que se ejecutan como servicios Docker independientes. Los MCPs proporcionan herramientas que pueden ser usadas por los agentes AI.

## Estructura

```
aifoundry/app/mcp_servers/
├── __init__.py
└── externals/                   # MCPs que corren en Docker
    ├── __init__.py
    ├── brave_search/
    │   ├── __init__.py
    │   ├── brave_search_mcp.py  # Configuración de conexión
    │   └── Dockerfile           # Imagen Docker
    └── playwright/
        ├── __init__.py
        ├── playwright_mcp.py    # Configuración de conexión
        └── Dockerfile           # Imagen Docker
```

## MCPs Disponibles

### 1. Brave Search MCP

**Propósito:** Búsquedas web usando la API de Brave Search.

**Puerto:** 8082

**Imagen Docker:** `aifoundry-brave-search-mcp:latest`

**Configuración:**
```bash
# .env
BRAVE_API_KEY=your-brave-api-key
BRAVE_SEARCH_MCP_URL=http://localhost:8082/mcp
```

### 2. Playwright MCP

**Propósito:** Automatización de navegador web (scraping, screenshots, etc.).

**Puerto:** 8931

**Imagen Docker:** `aifoundry-playwright-mcp:latest`

**Configuración:**
```bash
# .env
PLAYWRIGHT_MCP_URL=http://localhost:8931/mcp
```

## Uso

### Levantar los MCPs

```bash
# Levantar todos los MCPs
docker-compose up -d

# Ver logs
docker-compose logs -f brave-search-mcp
docker-compose logs -f playwright-mcp

# Detener
docker-compose down
```

### Probar MCPs

```bash
# Activar entorno virtual
source .venv/bin/activate

# Probar Brave Search MCP
PYTHONPATH=. python scripts/test_brave_mcp.py

# Probar Playwright MCP
PYTHONPATH=. python scripts/test_playwright_mcp.py
```

### Obtener Configuración de un MCP

```python
from aifoundry.app.mcp_servers.externals.brave_search import get_mcp_config
from aifoundry.app.mcp_servers.externals.playwright import get_mcp_config as get_playwright_config

# Configuración para langchain-mcp-adapters
brave_config = get_mcp_config()
# {'transport': 'streamable_http', 'url': 'http://localhost:8082/mcp'}

playwright_config = get_playwright_config()
# {'transport': 'streamable_http', 'url': 'http://localhost:8931/mcp'}
```

### Uso con MultiServerMCPClient

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from aifoundry.app.mcp_servers.externals.brave_search import get_mcp_config
from aifoundry.app.mcp_servers.externals.playwright import get_mcp_config as get_playwright_config

async def get_mcp_tools():
    client = MultiServerMCPClient({
        "brave_search": get_mcp_config(),
        "playwright": get_playwright_config(),
    })
    
    tools = await client.get_tools()
    return tools
```

## Agregar un Nuevo MCP

1. **Crear carpeta:** `aifoundry/app/mcp_servers/externals/{nombre_mcp}/`

2. **Crear `__init__.py`:**
```python
"""MCP Server Name."""
from .{nombre}_mcp import get_mcp_config
__all__ = ["get_mcp_config"]
```

3. **Crear configuración:** `{nombre_mcp}_mcp.py`
```python
from typing import Dict, Any
from aifoundry.app.config import settings

def get_mcp_config(headers: Dict[str, str] = None) -> Dict[str, Any]:
    config = {
        "transport": "streamable_http",
        "url": settings.{nombre_mcp}_url,
    }
    if headers:
        config["headers"] = headers
    return config
```

4. **Crear Dockerfile**

5. **Agregar al docker-compose.yml**

6. **Agregar variables a config.py y .env.example**

## Troubleshooting

### MCP no responde

```bash
# Verificar que el contenedor está corriendo
docker ps | grep mcp

# Ver logs
docker-compose logs brave-search-mcp

# Probar conexión
curl http://localhost:8082/mcp
```

### Error de API Key (Brave Search)

Asegúrate de tener `BRAVE_API_KEY` configurado en tu `.env`.

Obtén tu API Key en: https://brave.com/search/api/
