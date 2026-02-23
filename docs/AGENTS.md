# 🤖 Guía de Agentes - AIFoundry

> Documentación alineada con la arquitectura real del proyecto.

---

## 📖 Índice

1. [Arquitectura Real](#arquitectura-real)
2. [ScraperAgent — Agente Base](#scraperagent--agente-base)
3. [Config por Dominio](#config-por-dominio)
4. [Structured Output](#structured-output)
5. [Tools: Locales + MCP](#tools-locales--mcp)
6. [Memoria Conversacional](#memoria-conversacional)
7. [Crear un Nuevo Dominio](#crear-un-nuevo-dominio)
8. [API REST](#api-rest)
9. [Troubleshooting](#troubleshooting)

---

## Arquitectura Real

AIFoundry usa un **agente único genérico** (`ScraperAgent`) que se configura via JSON por dominio. No hay herencia de clases ni registry — cada dominio es un `config.json`.

### Stack Tecnológico

| Componente | Tecnología |
|------------|-----------|
| **Orquestación** | LangGraph (`create_agent` de `langchain.agents`) |
| **LLM** | LiteLLM proxy → multi-proveedor (OpenAI, Anthropic, etc.) |
| **Tools MCP** | `langchain-mcp-adapters` (Brave Search, Playwright) |
| **Tools locales** | `simple_scrape_url` (BeautifulSoup + Readability) |
| **API** | FastAPI |
| **Structured Output** | `response_format=` nativo de `create_agent` (Pydantic) |

### Diagrama

```
                    ┌─────────────────────┐
                    │     FastAPI API      │
                    │   (router.py)        │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │    ScraperAgent      │  ← agente único genérico
                    │   (base/agent.py)    │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
     ┌────────▼──────┐  ┌─────▼──────┐  ┌──────▼────────┐
     │ salary/       │  │electricity/│  │social_comments/│
     │ config.json   │  │config.json │  │config.json     │
     └───────────────┘  └────────────┘  └────────────────┘

     Tools:
     ├── brave_web_search (MCP - Docker)
     ├── playwright (MCP - Docker)
     └── simple_scrape_url (local)
```

### Estructura de Archivos

```
aifoundry/app/core/agents/
├── base/
│   ├── agent.py          # ScraperAgent — agente ReAct genérico
│   ├── config_schema.py  # Schema Pydantic para validar config.json
│   ├── prompts.py        # get_system_prompt(config) — prompt dinámico
│   └── tools.py          # get_local_tools() — simple_scrape_url
│
├── salary/
│   └── config.json       # Config específica de salarios
├── electricity/
│   └── config.json       # Config específica de electricidad
└── social_comments/
    └── config.json       # Config específica de comentarios sociales
```

---

## ScraperAgent — Agente Base

`ScraperAgent` es un agente ReAct que:

1. Recibe una config dict con `product`, `provider`, `country_code`, `query`, etc.
2. Genera un system prompt **dinámico** basado en esa config
3. Usa tools MCP (Brave, Playwright) + tools locales para scraping
4. Opcionalmente devuelve structured output via Pydantic

### Uso básico

```python
from aifoundry.app.core.agents.scraper.agent import ScraperAgent

async with ScraperAgent(use_mcp=True) as agent:
    result = await agent.run({
        "product": "electricity",
        "provider": "Endesa",
        "country_code": "ES",
        "language": "es",
        "query": "precio electricidad Endesa España febrero 2026",
    })
    print(result["output"])
```

### Uso con Structured Output (RECOMENDADO)

```python
from aifoundry.app.core.agents.scraper.agent import ScraperAgent
from aifoundry.app.schemas.agent_responses import SalaryResponse

async with ScraperAgent(
    use_mcp=True,
    response_model=SalaryResponse,  # ← structured output nativo, 1 sola llamada LLM
) as agent:
    result = await agent.run(config)
    structured = result["structured_response"]  # ← objeto Pydantic
```

### Parámetros del constructor

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `tools` | `List[BaseTool]` | `None` | Tools locales custom. Si None, usa `get_local_tools()` |
| `use_mcp` | `bool` | `True` | Cargar tools MCP (Brave, Playwright) |
| `disable_simple_scrape` | `bool` | `False` | Excluir `simple_scrape_url` |
| `verbose` | `bool` | `True` | Logging en tiempo real via callbacks |
| `use_memory` | `bool` | `True` | Memoria conversacional (InMemorySaver) |
| `response_model` | `Type[BaseModel]` | `None` | **RECOMENDADO**: Pydantic model para structured output nativo |
| `structured_output` | `bool` | `False` | **DEPRECATED**: Usa post-procesamiento (2 llamadas LLM) |
| `agent_name` | `str` | `None` | Nombre para debugging/tracing en LangGraph |

---

## Config por Dominio

Cada dominio tiene un `config.json` con la configuración específica:

```json
{
  "product": "salary",
  "query_template": "salario {position} {provider} {city} {country_name} {date}",
  "freshness": "py",
  "extraction_prompt": "Extrae salarios estructurados...",
  "validation_prompt": "Verifica que los datos sean coherentes...",
  "countries": {
    "ES": { "language": "es", "currency": "EUR" },
    "US": { "language": "en", "currency": "USD" }
  }
}
```

### Campos del config

| Campo | Descripción |
|-------|-------------|
| `product` | Tipo de producto (salary, electricity, social_comments) |
| `query_template` | Template para construir la query de búsqueda |
| `freshness` | Filtro temporal para Brave (`pw`=semana pasada, `py`=año pasado) |
| `extraction_prompt` | Prompt específico para extracción de datos del dominio |
| `validation_prompt` | Prompt específico para validación de datos |
| `countries` | Mapa de países con idioma y moneda |

---

## Structured Output

### Path NATIVO (recomendado) — 1 llamada LLM

Usa `response_model=` en el constructor. Internamente pasa `response_format=` a `create_agent`:

```python
from aifoundry.app.schemas.agent_responses import SalaryResponse

async with ScraperAgent(response_model=SalaryResponse) as agent:
    result = await agent.run(config)
    salary_data = result["structured_response"]  # SalaryResponse Pydantic object
```

### Path LEGACY (deprecated) — 2 llamadas LLM

Usa `structured_output=True`. Hace una segunda llamada LLM con `with_structured_output()`:

```python
# ⚠️ DEPRECATED — emite DeprecationWarning
async with ScraperAgent(structured_output=True) as agent:
    result = await agent.run(config)
```

### Modelos disponibles

Definidos en `aifoundry/app/schemas/agent_responses.py`:

| Modelo | Producto | Campos principales |
|--------|----------|--------------------|
| `SalaryResponse` | `salary` | `salaries[]`, `sources[]`, `summary`, `confidence` |
| `ElectricityResponse` | `electricity` | (por definir) |
| `SocialCommentsResponse` | `social_comments` | (por definir) |

---

## Tools: Locales + MCP

### Tools MCP (Docker)

| Tool | Servidor MCP | Transport | Descripción |
|------|-------------|-----------|-------------|
| `brave_web_search` | Brave Search | `streamable_http` | Búsqueda web con filtro de freshness |
| `browser_*` (navigate, snapshot, click, type, close) | Playwright | `streamable_http` | Navegación web completa |

### Tools Locales

| Tool | Descripción |
|------|-------------|
| `simple_scrape_url` | Scraping rápido con BeautifulSoup + Readability. Fallback antes de Playwright. |

### Nota sobre system_prompt

`create_agent` acepta `prompt=` pero es **estático** (se fija al crear el agente). Nuestro prompt es **dinámico** (cambia por país/producto/provider en cada `run()`), así que lo pasamos como `SystemMessage` en los messages de cada invocación. Esto es un patrón válido documentado en la API oficial.

---

## Memoria Conversacional

El agente usa `InMemorySaver` de LangGraph como checkpointer:

```python
# Multi-turn: el agente recuerda entre llamadas
async with ScraperAgent(use_memory=True) as agent:
    r1 = await agent.run(config1)  # El agente recuerda esto...
    r2 = await agent.run(config2)  # ...cuando procesa esto
    
    history = agent.get_history()  # Lista de mensajes
    print(agent.thread_id)         # ID del thread
```

### Reset de memoria

```python
agent.reset_memory()  # Nuevo InMemorySaver + nuevo thread_id
```

---

## Crear un Nuevo Dominio

Para añadir un nuevo dominio (ej: `real_estate`):

### 1. Crear el config.json

```bash
mkdir -p aifoundry/app/core/agents/real_estate
```

```json
// aifoundry/app/core/agents/real_estate/config.json
{
  "product": "real_estate",
  "query_template": "precio alquiler {type} {city} {country_name} {date}",
  "freshness": "pm",
  "extraction_prompt": "Extrae precios de alquiler...",
  "validation_prompt": "Verifica que los precios sean realistas...",
  "countries": {
    "ES": { "language": "es", "currency": "EUR" }
  }
}
```

### 2. Crear el modelo de respuesta (opcional)

```python
# aifoundry/app/schemas/agent_responses.py — añadir:
class RealEstateResponse(BaseModel):
    city: str
    prices: List[PriceEntry]
    sources: List[str]
    summary: str

# Añadir al mapping:
RESPONSE_MODELS["real_estate"] = RealEstateResponse
```

### 3. Usar desde la API

La API ya soporta cualquier producto que tenga `config.json`:

```bash
curl -X POST http://localhost:8000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"product": "real_estate", "provider": "Idealista", "country": "ES"}'
```

### 4. Test manual

```python
# scripts/test_real_estate_agent.py
from aifoundry.app.core.agents.scraper.agent import ScraperAgent
from aifoundry.app.schemas.agent_responses import RealEstateResponse

async with ScraperAgent(response_model=RealEstateResponse) as agent:
    result = await agent.run({
        "product": "real_estate",
        "provider": "Idealista",
        "country_code": "ES",
        "language": "es",
        "query": "precio alquiler piso Madrid España 2026",
    })
```

**No se necesita crear clases nuevas ni registrar nada** — solo el `config.json` y opcionalmente un modelo Pydantic.

---

## API REST

### Endpoint principal

```
POST /api/scrape
```

```json
{
  "product": "salary",
  "provider": "BCG",
  "country": "ES",
  "position": "Lead Architect",
  "city": "Madrid"
}
```

La API (`router.py`) automáticamente:
1. Carga el `config.json` del producto
2. Construye la query desde `query_template`
3. Instancia `ScraperAgent` con `response_model=` si existe modelo para el producto
4. Devuelve JSON estructurado o texto libre

---

## Troubleshooting

### El agente no encuentra datos

1. Verifica que Docker está corriendo (`docker-compose up -d`)
2. Verifica que los MCP servers responden: `curl http://localhost:8930/mcp` (Brave), `curl http://localhost:8931/mcp` (Playwright)
3. Revisa el `freshness` en config.json — `pw` (semana pasada) puede ser muy restrictivo

### Error de conexión MCP

```
Error cargando MCP tools: Connection refused
```

Los MCP servers corren en Docker. Ejecuta:
```bash
docker-compose up -d
```

### Structured output vacío

Si `result["structured_response"]` es `None`:
1. El LLM no generó datos suficientes para llenar el schema
2. Se usa fallback automático a post-procesamiento (segunda llamada LLM)
3. Revisa los logs: busca `"structured_response no encontrado"`

### Logs de debug

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("aifoundry").setLevel(logging.DEBUG)
```

---

## Referencias

- [LangChain Docs - Agents](https://python.langchain.com/docs/concepts/agents/)
- [LangChain API - create_agent](https://python.langchain.com/api_reference/langchain/agents.html)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [MCP Protocol](https://modelcontextprotocol.io/)