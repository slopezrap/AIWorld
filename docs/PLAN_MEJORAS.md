# 📋 Plan de Mejoras - AIFoundry

> Revisión técnica del proyecto contra la documentación oficial de LangChain (feb 2026) y buenas prácticas.
> Fecha: 18 febrero 2026

---

## 🔍 Auditoría del Estado Actual

### ✅ Lo que cumple con la documentación oficial

| Componente | Estado | Nota |
|------------|--------|------|
| `create_agent` de `langchain.agents` | ✅ Correcto | Es el API recomendado actualmente. Internamente crea un grafo LangGraph |
| `@tool` decorator para tools locales | ✅ Correcto | `tools.py` usa `@tool` de `langchain_core.tools`, forma estándar |
| `init_chat_model` para LLM factory | ✅ Correcto | `llm.py` usa `init_chat_model` con `openai` provider, forma recomendada |
| `MultiServerMCPClient` para MCP | ✅ Correcto | Integración correcta con `langchain-mcp-adapters` |
| `InMemorySaver` como checkpointer | ✅ Correcto | Patrón estándar de LangGraph para persistencia de estado |
| `SystemMessage` + `HumanMessage` | ✅ Correcto | Forma estándar de construir mensajes |
| Callbacks (`BaseCallbackHandler`) | ✅ Correcto | `AgentCallbackHandler` implementa correctamente el patrón de callbacks |
| Structured output con Pydantic | ✅ Correcto | Usa `with_structured_output()` como post-procesamiento |
| Patrón ReAct | ✅ Correcto | `create_agent` implementa ReAct por defecto |

### ⚠️ Lo que necesita mejora

| Componente | Problema | Referencia docs |
|------------|----------|-----------------|
| FastAPI sin endpoints | App creada pero sin rutas REST para agentes | FastAPI best practices |
| Sin validación de configs | `config.json` se carga con `json.load()` sin validar schema | Pydantic BaseSettings |
| Sin retry en LLM calls | Si `litellm` falla no hay backoff exponencial | `tenacity` (ya en deps) |
| Prompts hardcodeados en código | `prompts.py` tiene la estructura fija, no viene del config | LangChain PromptTemplate |
| Sin tests unitarios | `aifoundry/tests/` está vacío | pytest + pytest-asyncio |
| `response_format` no usado en `create_agent` | Se hace post-proceso manual en vez de usar el parámetro nativo | `create_agent(response_format=...)` |

---

## 🛠 Plan de Implementación

### Tarea 1: Completar FastAPI con Endpoints REST (🔴 Alta)

**Problema**: `main.py` tiene FastAPI configurado (CORS, lifespan) pero sin ningún endpoint. Los agentes solo se ejecutan desde scripts manuales.

**Solución**: Crear un router `api/agents.py` con endpoint genérico que use el `AgentFactory` existente.

**Archivos a crear/modificar**:
- [ ] Crear `aifoundry/app/api/__init__.py`
- [ ] Crear `aifoundry/app/api/agents.py` — Router con endpoints
- [ ] Crear `aifoundry/app/api/schemas.py` — Request/Response models para la API
- [ ] Modificar `aifoundry/app/main.py` — Registrar el router

**Endpoint principal**:
```
POST /api/agents/{agent_name}/run
```

**Request body**:
```json
{
  "provider": "Endesa",
  "country": "ES",
  "config_overrides": {}  // opcional
}
```

**Response**:
```json
{
  "agent": "electricity",
  "status": "success",
  "data": { ... },  // structured output del agente
  "metadata": {
    "execution_time_seconds": 12.5,
    "steps_count": 7
  }
}
```

**Endpoints adicionales**:
```
GET  /api/agents              — Lista agentes disponibles
GET  /api/agents/{name}/config — Devuelve config del agente
GET  /health                   — Health check
```

**Buenas prácticas aplicadas**:
- Usar `APIRouter` con prefijo `/api`
- Modelos Pydantic para request/response
- Manejo de errores con `HTTPException`
- Timeout configurable para ejecución de agentes
- Logging estructurado

---

### Tarea 2: Tests Unitarios con pytest (🔴 Alta)

**Problema**: Directorio `aifoundry/tests/` vacío. Solo hay scripts manuales en `scripts/`.

**Solución**: Crear suite de tests unitarios con pytest + pytest-asyncio (ya están en dependencies).

**Archivos a crear**:
- [ ] `aifoundry/tests/conftest.py` — Fixtures compartidos
- [ ] `aifoundry/tests/test_prompts.py` — Tests de generación de prompts
- [ ] `aifoundry/tests/test_config_validation.py` — Tests de validación de configs
- [ ] `aifoundry/tests/test_utils_text.py` — Tests de `extract_json`, `clean_text`
- [ ] `aifoundry/tests/test_utils_country.py` — Tests de `get_country_info`, `get_brave_config`
- [ ] `aifoundry/tests/test_rate_limiter.py` — Tests del `AsyncRateLimiter`
- [ ] `aifoundry/tests/test_api.py` — Tests de endpoints con `httpx.AsyncClient`

**Qué testear**:

| Módulo | Tests |
|--------|-------|
| `prompts.py` | Generación correcta de system prompt con distintas configs, fecha en español, traducción de idiomas |
| `text.py` | `extract_json` con JSON válido, inválido, embebido en texto, array vs object |
| `country.py` | `get_country_info` para países existentes y no existentes, `get_brave_config` |
| `rate_limiter.py` | Que respete el rate limit, que no bloquee bajo el límite |
| `agent_responses.py` | Que `get_response_schema` devuelva el schema correcto por nombre |
| `api/agents.py` | Endpoints responden correctamente, errores 404 para agentes inexistentes |
| `AgentConfig` (nuevo) | Validación de configs válidos e inválidos |

**Buenas prácticas**:
- Fixtures para configs de ejemplo
- Mocking de llamadas a LLM (no tests de integración costosos)
- `pytest.mark.asyncio` para tests async
- Cobertura mínima objetivo: utils y prompts al 90%

---

### Tarea 3: Validar config.json con Pydantic (🟡 Media)

**Problema**: Los `config.json` se cargan con `json.load()` sin validación. Si falta un campo o tiene un tipo incorrecto, el error aparece mucho después en la ejecución.

**Solución**: Crear modelo `AgentConfig` con Pydantic que valide al cargar.

**Archivos a crear/modificar**:
- [ ] Crear `aifoundry/app/core/agents/base/config.py` — Modelo `AgentConfig`
- [ ] Modificar `aifoundry/app/core/agents/base/agent.py` — Usar `AgentConfig` al cargar config

**Modelo propuesto**:
```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class CountryConfig(BaseModel):
    providers: List[str] = Field(..., min_length=1)
    language: str = Field(..., pattern=r'^[a-z]{2}$')

class AgentConfig(BaseModel):
    product: str = Field(..., min_length=1)
    freshness: str = Field(default="pw")
    query_template: str = Field(...)
    countries: Dict[str, CountryConfig]
    extraction_prompt: Optional[str] = None
    validation_prompt: Optional[str] = None
    response_schema: Optional[Dict] = None

    @classmethod
    def from_json(cls, path: str) -> "AgentConfig":
        import json
        with open(path) as f:
            return cls(**json.load(f))
```

**Beneficios**:
- Errores claros al cargar: `"field 'product' is required"`
- Autocompletado en IDE
- Documentación implícita del schema
- Serialización/deserialización gratis

---

### Tarea 4: Mover Templates de Prompts al Config (🟡 Media)

**Problema**: `prompts.py` tiene una estructura fija de 7 pasos hardcodeada. Los únicos campos que vienen del config son `extraction_prompt` y `validation_prompt` (pasos 6 y 7). El resto del prompt es idéntico para todos los agentes.

**Análisis**: Para el caso actual (todos los agentes son "scrapers web"), la estructura de 7 pasos compartida tiene sentido. Pero si quisieras un agente que NO haga scraping (ej: un agente de RAG o un chatbot), no podría reusar esos prompts.

**Solución**: Hacer el system prompt configurable por agente, manteniendo un default para los scrapers.

**Archivos a modificar**:
- [ ] Modificar configs JSON — Añadir campo opcional `system_prompt_template`
- [ ] Modificar `aifoundry/app/core/agents/base/prompts.py` — Soportar template personalizado
- [ ] Modificar `aifoundry/app/core/agents/base/config.py` — Añadir campo al modelo

**Estrategia**:
```json
{
  "product": "electricidad",
  "system_prompt_template": null,  // null = usa el default de 7 pasos
  "extraction_prompt": "...",      // personaliza solo paso 6
  "validation_prompt": "..."       // personaliza solo paso 7
}
```

Si `system_prompt_template` es `null`, se usa el prompt de 7 pasos actual (retrocompatible). Si se proporciona, se usa como template con variables `{product}`, `{provider}`, `{country}`, `{date}`, etc.

---

### Tarea 5: Retry con Backoff Exponencial (🟡 Media)

**Problema**: En `agent.py`, las llamadas al LLM se hacen sin retry. Si hay un error de red o rate limit, falla directamente. Aunque hay un `max_retries` en el agente, solo cubre errores muy específicos de scraping, no errores de la API del LLM.

**Solución**: Usar `tenacity` (ya está en `pyproject.toml`) para retry con backoff exponencial en `get_llm()` o en el wrapper del agente.

**Archivos a modificar**:
- [ ] Modificar `aifoundry/app/core/models/llm.py` — Añadir retry config al modelo
- [ ] Modificar `aifoundry/app/core/agents/base/agent.py` — Wrap de invocación con retry

**Implementación**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

# En llm.py - configurar max_retries del modelo
def get_llm() -> BaseChatModel:
    ...
    _llm_instance = init_chat_model(
        settings.litellm_model,
        model_provider="openai",
        temperature=settings.litellm_temperature,
        max_retries=3,  # <-- Añadir retry nativo de LangChain
        request_timeout=120,  # <-- Timeout explícito
        ...
    )
```

**Nota**: `init_chat_model` con provider `openai` ya soporta `max_retries` de forma nativa a nivel de llamada HTTP. Esto es más limpio que un wrapper con tenacity porque maneja los retry-after headers automáticamente.

---

## 📊 Orden de Implementación

```
Tarea 3 (Pydantic config)     ← Base para todo lo demás
    ↓
Tarea 4 (Prompts al config)   ← Depende de tener AgentConfig
    ↓
Tarea 5 (Retry LLM)           ← Independiente, rápido
    ↓
Tarea 1 (FastAPI endpoints)   ← Usa AgentConfig para listar/validar
    ↓
Tarea 2 (Tests)               ← Testea todo lo anterior
```

---

## ✅ Checklist de Ejecución

- [ ] **Tarea 3**: Crear `AgentConfig` Pydantic + integrar en `agent.py`
- [ ] **Tarea 4**: System prompt configurable por agente
- [ ] **Tarea 5**: Retry con `max_retries` + timeout en `get_llm()`
- [ ] **Tarea 1**: Router FastAPI con endpoints REST
- [ ] **Tarea 2**: Tests unitarios con pytest
- [ ] Verificar que todos los scripts de test siguen funcionando
- [ ] Actualizar `README.md` con los nuevos endpoints
- [ ] Actualizar `docs/AGENTS.md` con la nueva configuración

---

## 🔑 Nota sobre `response_format` en `create_agent`

La documentación actual de LangChain muestra que `create_agent` acepta `response_format` como parámetro para forzar structured output. Tu código actual hace un post-procesamiento con `_convert_to_structured()` usando `llm.with_structured_output()`. 

**Recomendación**: Mantener tu enfoque actual de post-procesamiento. El `response_format` nativo de `create_agent` tiene limitaciones documentadas:
1. No todos los modelos lo soportan
2. Puede interferir con tool calling en algunos providers
3. Tu approach de "dejar que el agente trabaje libre y luego estructurar" es más robusto

Esto NO es un problema a arreglar, es una decisión de diseño correcta.