# AIWorld

**Plataforma de agentes de AI para investigación web y extracción de datos estructurados.**

AIWorld está compuesto por dos componentes principales:

| Componente | Descripción | Stack |
|------------|-------------|-------|
| **AIFoundry** (Backend) | API de agentes de AI con scraping web, búsqueda y structured output | Python · FastAPI · LangGraph · LiteLLM · MCP |
| **AIWorld Client** (Frontend) | Interfaz conversacional tipo Cline para Microsoft Teams | React · TypeScript · Teams SDK · SSE |

---

## Arquitectura

```
┌──────────────────────────────────────────────────────┐
│                  AIWorld Client                       │
│         React SPA / Microsoft Teams Tab App          │
│                                                      │
│  ┌─────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Sidebar  │  │  Chat Panel  │  │ Structured     │  │
│  │ Agents   │  │  Messages    │  │ Data Tables    │  │
│  │ Sessions │  │  Tool Blocks │  │ Charts         │  │
│  └─────────┘  └──────────────┘  └────────────────┘  │
└──────────────────────┬───────────────────────────────┘
                       │ REST + SSE
┌──────────────────────▼───────────────────────────────┐
│                    AIFoundry                          │
│              FastAPI Backend (Python)                 │
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │             ScraperAgent (ReAct)              │    │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────────┐  │    │
│  │  │ Memory   │ │ Tool     │ │ Output      │  │    │
│  │  │ Manager  │ │ Resolver │ │ Parser      │  │    │
│  │  └──────────┘ └──────────┘ └─────────────┘  │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
│  ┌───────────────┐  ┌───────────────────────────┐    │
│  │ LLM (LiteLLM) │  │ MCP Servers               │    │
│  │ Claude/GPT/... │  │ ┌─────────┐ ┌──────────┐ │    │
│  └───────────────┘  │ │ Brave   │ │Playwright│ │    │
│                      │ │ Search  │ │ Browser  │ │    │
│                      │ └─────────┘ └──────────┘ │    │
│                      └───────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

---

## AIFoundry (Backend)

### ¿Qué es?

AIFoundry es un backend de agentes de AI que investigan la web, extraen datos y los devuelven como objetos Pydantic estructurados. Usa un único agente genérico (`ScraperAgent`) que se configura vía JSON para cada dominio.

### Dominios disponibles

| Dominio | Config | Structured Output | Descripción |
|---------|--------|-------------------|-------------|
| **Salarios** | `salary/config.json` | `SalaryResponse` | Investiga salarios por empresa, puesto y país |
| **Electricidad** | `electricity/config.json` | `ElectricityResponse` | Precios de electricidad por país y proveedor |
| **Comentarios Sociales** | `social_comments/config.json` | `SocialCommentsResponse` | Monitoriza opiniones en redes sociales |

### Stack tecnológico

| Tecnología | Propósito |
|------------|-----------|
| **LangGraph** | Runtime de agentes ReAct con checkpointer |
| **LangChain** | Orquestación de LLMs y tools |
| **LiteLLM** | Proxy multi-proveedor (Bedrock, OpenAI, Anthropic) |
| **FastAPI** | API REST con docs OpenAPI automáticas |
| **MCP** | Model Context Protocol para tools externas |
| **Pydantic** | Validación de datos y structured output |

### Estructura del proyecto

```
aifoundry/
├── app/
│   ├── api/                    # Endpoints FastAPI
│   │   ├── router.py           # Routes: /health, /agents, /agents/{name}/run
│   │   └── schemas.py          # Request/Response schemas
│   ├── config.py               # Settings (Pydantic BaseSettings)
│   ├── main.py                 # FastAPI app + lifespan
│   ├── core/
│   │   ├── agents/
│   │   │   └── scraper/             # Agente genérico de scraping
│   │   │       ├── agent.py         # ScraperAgent (orquestador)
│   │   │       ├── memory.py        # InMemoryManager / NullMemoryManager
│   │   │       ├── tool_executor.py # ToolResolver (MCP + local tools)
│   │   │       ├── output_parser.py # OutputParser (structured + text)
│   │   │       ├── prompts.py       # System prompt builder
│   │   │       ├── tools.py         # Local tools (scraper, country info)
│   │   │       ├── config_schema.py # AgentConfig Pydantic model
│   │   │       ├── salary/          # config.json para salarios
│   │   │       ├── electricity/     # config.json para electricidad
│   │   │       └── social_comments/ # config.json para redes sociales
│   │   └── models/
│   │       └── llm.py          # LLM singleton (init_chat_model + LiteLLM)
│   ├── mcp_servers/            # Servidores MCP (Brave Search, Playwright)
│   ├── schemas/                # Response models (SalaryResponse, etc.)
│   └── utils/                  # Utilidades (parsing, scraping, country info)
├── tests/                      # 230 tests (unit + integration)
└── docker/                     # Dockerfiles
```

### API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/agents` | Lista de agentes disponibles |
| `GET` | `/api/agents/{name}/config` | Configuración de un agente |
| `POST` | `/api/agents/{name}/run` | Ejecuta un agente (síncrono) |

### Instalación y ejecución

```bash
# 1. Clonar el repositorio
git clone https://github.com/slopezrap/AIWorld.git
cd AIWorld

# 2. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate

# 3. Instalar dependencias
pip install -e ".[dev]"

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys

# 5. Levantar servicios MCP (Docker)
docker compose up -d

# 6. Ejecutar el servidor
uvicorn aifoundry.app.main:app --reload --port 8000
```

### Configuración (.env)

```bash
# LLM
LITELLM_API_BASE=https://your-litellm-proxy.com
LITELLM_API_KEY=sk-your-key
LITELLM_MODEL=bedrock/claude-sonnet-4

# MCP Servers
BRAVE_SEARCH_MCP_URL=http://localhost:8082/mcp
PLAYWRIGHT_MCP_URL=http://localhost:8931/mcp

# Brave Search
BRAVE_API_KEY=your-brave-key
```

### Tests

```bash
# Ejecutar todos los tests (230)
python -m pytest aifoundry/tests/ -v

# Tests unitarios
python -m pytest aifoundry/tests/unit/ -v

# Tests de integración
python -m pytest aifoundry/tests/integration/ -v

# Scripts de test end-to-end (requiere servicios MCP + LLM)
python scripts/test_salary_agent.py
python scripts/test_electricity_agent.py
python scripts/test_social_comments_agent.py
```

### Crear un nuevo dominio

Para añadir un nuevo tipo de agente (ej: precios de gasolina):

1. **Crear config.json** en `aifoundry/app/core/agents/scraper/fuel/config.json`
2. **Crear response model** en `aifoundry/app/schemas/agent_responses.py`
3. El discovery automático del router lo detecta (busca `**/config.json` recursivamente)

No se necesita crear clases Python — `ScraperAgent` es genérico y se adapta vía config.

---

## AIWorld Client (Frontend) — En desarrollo

### Visión

Interfaz conversacional inspirada en Cline, adaptada para usuarios no técnicos. Se integra como **Microsoft Teams Tab App** para acceso directo desde el entorno corporativo.

### Características planificadas

- **Formularios dinámicos** por agente (en vez de prompt libre)
- **Tool Blocks** expandibles estilo Cline (ver qué está haciendo el agente en tiempo real)
- **Streaming SSE** para respuestas progresivas
- **Tablas de datos estructurados** con export a Excel
- **Historial de sesiones** con memoria conversacional
- **Tema corporativo** con soporte dark/light

### Stack planificado

| Tecnología | Propósito |
|------------|-----------|
| **React 18+** | UI framework |
| **TypeScript** | Type safety |
| **Vite** | Build tool |
| **Zustand** | State management |
| **TanStack Query** | Server state + cache |
| **Fluent UI** | Componentes Microsoft |
| **Teams SDK** | Integración Microsoft Teams |

### Fases de desarrollo

| Fase | Descripción | Estado |
|------|-------------|--------|
| **Phase 1 — MVP** | Polling async: formularios, respuestas, datos estructurados | 📋 Planificado |
| **Phase 2 — Streaming** | SSE para tool blocks en tiempo real, UX tipo Cline | 📋 Planificado |
| **Phase 3 — Teams** | Empaquetado como Teams Tab App, auth SSO | 📋 Planificado |

> Ver `docs/FRONTEND_DESIGN_PROPOSAL.md` para el diseño detallado.

---

## Documentación

| Documento | Descripción |
|-----------|-------------|
| `docs/AGENTS.md` | Guía completa de agentes: configuración, tools, structured output |
| `docs/MCP.md` | Arquitectura MCP: Brave Search y Playwright |
| `docs/FRONTEND_DESIGN_PROPOSAL.md` | Propuesta de diseño del frontend |
| `docs/REFACTORING_CHECKLIST.md` | Checklist de refactoring del backend |

---

## Roadmap

### ✅ Completado

- Agente ReAct genérico (`ScraperAgent`) con config JSON por dominio
- Structured output nativo via `response_format` (1 sola llamada LLM)
- Integración MCP (Brave Search + Playwright)
- Memoria conversacional con `InMemorySaver`
- API REST con FastAPI
- 230 tests unitarios y de integración
- Refactoring modular: `memory.py`, `tool_executor.py`, `output_parser.py`

### 🔧 En progreso

- [ ] Autenticación API Key (`X-API-Key` header)
- [ ] Streaming SSE (`POST /agents/{name}/stream`)
- [ ] Memoria persistente (Redis + SQLite fallback)

### 📋 Planificado

- [ ] Frontend React (AIWorld Client)
- [ ] Integración Microsoft Teams
- [ ] Multi-agent workflows
- [ ] RAG con vector DB

---

## Licencia

MIT