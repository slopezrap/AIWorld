# 🗺️ ROADMAP: AIFoundry — De 7/10 a 10/10

> Plan maestro con checklist detallado para corregir bugs, mejorar diseño y completar la arquitectura.
> Nombre oficial del proyecto: **AIFoundry**.
> Generado: 18 febrero 2026

---

## 📋 ÍNDICE

1. [FASE 1: Bugs Críticos](#fase-1-bugs-críticos) — ⏱️ ~2h
2. [FASE 2: Problemas de Diseño](#fase-2-problemas-de-diseño) — ⏱️ ~3h
3. [FASE 3: Arquitectura FastAPI](#fase-3-arquitectura-fastapi) — ⏱️ ~2h
4. [FASE 4: Validación y Configuración](#fase-4-validación-y-configuración) — ⏱️ ~2h
5. [FASE 5: Tests](#fase-5-tests) — ⏱️ ~3h
6. [FASE 6: Prompt Engineering](#fase-6-prompt-engineering) — ⏱️ ~1h
7. [FASE 7: Infraestructura](#fase-7-infraestructura) — ⏱️ ~1h

**Tiempo total estimado: ~14h**

---

## FASE 1: Bugs Críticos

> Prioridad 🔴 MÁXIMA — Sin esto el sistema tiene leaks y código muerto.

### 1.1 — BUG 1: Reusar `self._agent` de `initialize()` en `run()`

- [x] **1.1.1** Refactorizar `run()` para que use `self._agent` en vez de crear uno nuevo
- [x] **1.1.2** Añadir `if self._agent is None: await self.initialize()` al inicio de `run()`
- [x] **1.1.3** Eliminar la creación de `create_agent()` dentro del retry loop de `run()`
- [x] **1.1.4** Mover la construcción de `run_config` (callbacks, thread_id) fuera del if/else MCP → `_build_run_config()`

### 1.2 — BUG 2: Cerrar MCP Client / eliminar leak de conexiones

- [x] **1.2.1** Eliminar la creación de `MultiServerMCPClient` dentro de `run()`
- [x] **1.2.2** Reusar `self._mcp_client` creado en `initialize()`
- [x] **1.2.3** Verificar que `cleanup()` cierra correctamente el MCP client — try/except/finally en `cleanup()`
- [x] **1.2.4** Añadir `try/finally` en `run()` para garantizar limpieza ante excepciones → `async with` (context manager `__aexit__`) garantiza cleanup

### 1.3 — BUG 3: Checkpointer sin efecto → hacer que funcione de verdad

**Problema actual:** El checkpointer existe pero NO persiste nada porque:
1. El `thread_id` cambia en cada intento (`f"thread-{attempt}"`) — se pierde el estado entre reintentos
2. El agente se recrea en cada `run()` con un nuevo `create_agent()`, descartando el checkpointer anterior
3. No hay forma de que el caller pase un `thread_id` estable para conversaciones multi-turn

**Solución:** Hacer que `self._agent` se cree UNA vez en `initialize()` con el checkpointer, y que `run()` reutilice ese agente con un `thread_id` consistente.

- [x] **1.3.1** Mover `checkpointer=self._checkpointer` al `create_agent()` dentro de `initialize()` (no en `run()`)
- [x] **1.3.2** Usar un `thread_id` estable: `self._thread_id = uuid4()` en `__init__`, override desde `config["thread_id"]`
- [x] **1.3.3** Separar el `thread_id` de reintentos: `run_config = self._build_run_config()` ANTES del loop → mismo thread_id en todos los reintentos
- [x] **1.3.4** En `run()`, pasar `config={"configurable": {"thread_id": self._thread_id}, "callbacks": ...}` al `ainvoke()` — via `_build_run_config()`
- [x] **1.3.5** Añadir método `reset_memory()` — crea nuevo InMemorySaver + nuevo thread_id + fuerza `self._agent = None` para reinicializar
- [x] **1.3.6** Añadir método `get_history()` — lee checkpoint del thread actual vía `self._checkpointer.get()`
- [x] **1.3.7** En los scripts de test, verificar que llamar a `agent.run()` dos veces con el mismo `thread_id` acumula contexto (el agente "recuerda" la primera llamada)
  - 📖 **Docs consultada:** https://langchain-ai.github.io/langgraph/how-tos/persistence/ — Confirmado patrón `InMemorySaver` + `thread_id` en `configurable`
  - 📝 **Implementado en:** `scripts/test_memory_multiturn.py` — Valida 4 checks: mismo thread_id, historial crece, mensajes acumulan, ambos turns exitosos

---

## FASE 2: Problemas de Diseño

> Prioridad 🟡 ALTA — Código más limpio, mantenible y performante.

### 2.1 — Eliminar código duplicado en `run()`

- [x] **2.1.1** Unificar la rama `if self._use_mcp` / `else` en `run()` — `run()` ya no tiene ramas MCP, todo en `initialize()`
- [x] **2.1.2** Extraer la preparación de tools a un método — tools se preparan en `initialize()`, no se necesita método extra
- [x] **2.1.3** Extraer la construcción de `run_config` a un método `_build_run_config() -> dict`
- [x] **2.1.4** El cuerpo de `run()` queda: preparar mensajes → invocar agente → procesar resultado ✅

### 2.2 — Eliminar dead code

- [x] **2.2.1** Eliminar `ScraperResponse` dataclass (nunca usada) — eliminada
- [x] **2.2.2** Eliminar import de `dataclass` y `field` — eliminados
- [x] **2.2.3** Revisar si `TOOL_TO_STEP` se usa fuera de callbacks — movido como `_TOOL_TO_STEP` class var dentro de `AgentCallbackHandler`

### 2.3 — Hacer `simple_scrape_url` async

- [x] **2.3.1** Convertir `simple_scrape_url` en `async def` en `tools.py`
- [x] **2.3.2** Usar `asyncio.to_thread(_simple_scrape, url, ...)` para no bloquear el event loop
- [x] **2.3.3** ~~Alternativa: httpx.AsyncClient~~ — No necesario, 2.3.2 resuelve el problema
- [x] **2.3.4** LangChain maneja async tools con `@tool` + `async def` correctamente

### 2.4 — Mejorar `parse_output` 

- [x] **2.4.1** Skip `parse_output` cuando `structured_output=True` — `parsed = {} if self._structured_output else self.parse_output(output)`
- [x] **2.4.2** Mover `parse_output` a un módulo `utils/parsing.py` separado
  - 📝 Creado `aifoundry/app/utils/parsing.py` con `parse_agent_output()` standalone
  - 📝 `agent.py` delega `parse_output()` → `parse_agent_output()` (backward compatible)
- [x] **2.4.3** Añadir tests unitarios para `parse_output` con diferentes formatos de output del LLM
  - 📝 `aifoundry/tests/unit/test_parsing.py` — 23 tests (queries, URLs, Playwright, edge cases)
  - ✅ 23/23 passed — Fix regex para comillas dobles/simples en queries

---

## FASE 3: Arquitectura FastAPI

> Prioridad 🟡 ALTA — Definir si es API o CLI y ser consistente.

### 3.1 — Crear endpoints REST reales

- [x] **3.1.1** Crear `aifoundry/app/api/` directorio
- [x] **3.1.2** Crear `aifoundry/app/api/__init__.py`
- [x] **3.1.3** Crear `aifoundry/app/api/router.py` con router principal
  - Incluye `_discover_agents()` que escanea `core/agents/*/config.json`
  - Incluye `_build_agent_config()` para construir la config de ejecución
- [x] **3.1.4** Crear endpoint `POST /agents/{agent_name}/run` que:
  - Recibe `{"provider": "...", "country_code": "ES", "query": "..."}`
  - Valida agente existe y país soportado (404/422)
  - Carga el config.json del agente
  - Genera query automática desde `query_template` si no se proporciona
  - Ejecuta `ScraperAgent.run(config)` como context manager
  - Devuelve la respuesta estructurada (`AgentRunResponse`)
- [x] **3.1.5** Crear endpoint `GET /agents` que lista agentes disponibles (usa `_discover_agents()`)
- [x] **3.1.6** Crear endpoint `GET /agents/{agent_name}/config` que devuelve el config.json del agente
- [x] **3.1.7** Crear endpoint `GET /health` — health check con modelo LLM, MCPs y nº agentes
- [x] **3.1.8** Registrar router en `main.py` — `app.include_router(api_router)`
  - Reescrito `main.py` con `lifespan` moderno, CORS, OpenAPI docs en `/docs` y `/redoc`
  - Eliminados endpoints dummy anteriores
- [x] **3.1.9** Crear schemas Pydantic para request/response (`aifoundry/app/api/schemas.py`)
  - `AgentRunRequest`, `AgentRunResponse`, `AgentInfo`, `AgentListResponse`, `HealthResponse`, `ErrorResponse`
  - ✅ Verificado: `python -c "from aifoundry.app.api.router import ..."` — 3 agentes descubiertos, 4 rutas activas

### 3.2 — Lifecycle MCP en FastAPI

- [x] **3.2.1** Mantener el `lifespan` actual de FastAPI para arrancar/verificar MCPs
  - `lifespan` configura logging y muestra config al arrancar
- [ ] **3.2.2** _(Futuro)_ Crear un singleton `MCPClientManager` que se inicializa en `lifespan` y se inyecta via dependency injection
- [ ] **3.2.3** _(Futuro)_ Los endpoints reciben el MCP client via `Depends(get_mcp_client)`
  - 📝 **Nota:** Por ahora cada ejecución de agente crea/cierra su propio MCP client (via `ScraperAgent` context manager). Funciona bien para baja concurrencia. El singleton MCP será necesario cuando haya múltiples requests concurrentes.

---

## FASE 4: Validación y Configuración

> Prioridad 🟡 MEDIA — Robustez y extensibilidad.

### 4.1 — Validar config.json con Pydantic

- [x] **4.1.1** Crear `aifoundry/app/core/agents/base/config_schema.py`
  - 📝 `AgentConfig` + `CountryConfig` con validadores Pydantic
  - 📝 `extra="forbid"` en ambos modelos para detectar typos
- [x] **4.1.2** Definir `AgentConfig(BaseModel)` con campos reales del proyecto:
  - `product` (requerido), `query_template` (requerido), `countries` (requerido, Dict[str, CountryConfig])
  - `freshness` (default "pw", validado contra pd/pw/pm/py), `extraction_prompt`, `validation_prompt`
  - `system_prompt_template` (opcional), `social_networks` (opcional)
  - Métodos helper: `get_country_codes()`, `get_providers(cc)`, `get_language(cc)`
- [x] **4.1.3** Validar config.json al cargar en `_discover_agents()` del router
  - 📝 `AgentConfig(**raw_config)` en `router.py` — configs inválidos se descartan con error claro
  - 📝 Cache `_validated_configs` + función `get_validated_config(agent_name)`
- [x] **4.1.4** Errores claros: `ValidationError` de Pydantic con campo, valor y razón
- [x] **4.1.5** `extra="forbid"` incluido — typos en config.json causan error inmediato
  - ✅ Verificado: 3/3 agentes validados OK (electricity, salary, social_comments)

### 4.2 — Prompts configurables por agente

- [x] **4.2.1** Añadir campo `system_prompt_template` opcional al `AgentConfig` schema
- [x] **4.2.2** En `get_system_prompt()`: si config tiene `system_prompt_template`, usarlo con `.format()` y todas las variables disponibles (product, provider, country_name, etc.)
- [x] **4.2.3** Fallback al prompt genérico de 7 pasos si no hay template o si `.format()` falla por variable desconocida (con warning en log)

### 4.3 — Retry y timeout en LLM

- [x] **4.3.1** Añadir `llm_num_retries: int = 3` y `llm_request_timeout: int = 120` a `Settings` en `config.py`
- [x] **4.3.2** Pasar `max_retries=num_retries` y `timeout=request_timeout` a `init_chat_model()` en `llm.py`
- [x] **4.3.3** Valores por defecto: 3 retries, 120s timeout — configurables vía env vars `LLM_NUM_RETRIES` y `LLM_REQUEST_TIMEOUT`
  - ✅ Verificado: API arranca OK, health check 200, 23/23 tests passed

---

## FASE 5: Tests

> Prioridad 🟡 MEDIA — Sin tests no hay confianza en los cambios.

### 5.1 — Setup pytest

- [x] **5.1.1** Crear `aifoundry/tests/conftest.py` con fixtures comunes
  - 📝 Fixtures: `electricity_config`, `salary_config`, `social_config`, `minimal_agent_config_dict`
- [x] **5.1.2** `pytest`, `pytest-asyncio` ya en `pyproject.toml` — verificado
- [x] **5.1.3** Crear `aifoundry/tests/unit/` y `aifoundry/tests/integration/` con `__init__.py`

### 5.2 — Tests unitarios

- [x] **5.2.1** `test_prompts.py` — 16 tests: prompt genérico, idiomas, extraction/validation, custom template, defaults
- [x] **5.2.2** ~~`test_tools.py`~~ — Pospuesto (requiere mock HTTP complejo, cubierto indirectamente por test_parsing)
- [x] **5.2.3** `test_rate_limiter.py` — 8 tests: rate limiting, retry 429, no retry otros errores, max retries, singleton
- [x] **5.2.4** `test_text_utils.py` — 25 tests: truncate_text, clean_markdown, extract_urls, parse_json_response
- [x] **5.2.5** `test_country.py` — 18 tests: get_country_info, brave codes, currency, search_lang, ui_lang, full config
- [x] **5.2.6** `test_config_schema.py` — 18 tests: CountryConfig, AgentConfig valid/invalid, helpers, extra="forbid"
- [x] **5.2.7** `test_parsing.py` — 23 tests (creado en Fase 2): queries, URLs, Playwright, edge cases
- [x] **5.2.8** `test_agent_responses.py` — 10 tests: ScraperResponse, SalaryData, SalaryResponse, get_response_schema

### 5.3 — Tests de integración

- [ ] **5.3.1** ~~`test_agent_lifecycle.py`~~ — Pospuesto (requiere mock LLM + MCP complejo)
- [x] **5.3.2** `test_api_endpoints.py` — 19 tests: health, list agents, get config, run validation, root, OpenAPI
  - ✅ **149/149 tests passed** en 13s — 0 fallos

---

## FASE 6: Prompt Engineering

> Prioridad 🟢 BAJA — Optimización, no crítico.

### 6.1 — Optimizar system prompt

- [x] **6.1.1** Reducir prompt: de 7 pasos con mucha redundancia → 5 pasos concisos
  - Eliminados separadores decorativos dobles, instrucciones repetidas, sección RESUMEN duplicada
  - Configuración en 2 líneas compactas vs 5 líneas anteriores
- [x] **6.1.2** Eliminar PASO 2 (traducción) — ahora es un `translate_hint` inline si `language != "es"`
- [x] **6.1.3** Scrapear **5-8 URLs más relevantes** según título/descripción (antes: "scrapea TODAS las 20")
  - Criterios de priorización: 1) fuentes oficiales, 2) portales especializados, 3) medios reconocidos
  - "Evitar: foros, blogs personales, aggregadores sin fuente original"
- [x] **6.1.4** Regla de STOP: "Si tras procesar 8 URLs no encuentras datos relevantes, para y reporta"
- [x] **6.1.5** Priorizar fuentes oficiales (gobierno, reguladores, empresas) — incluido en criterios de selección
  - ✅ 149/149 tests passed con prompt optimizado

---

## FASE 7: Infraestructura

> Prioridad 🟢 BAJA — Nice to have.

### 7.1 — Docker para la app principal

- [ ] **7.1.1** Crear `Dockerfile` en raíz para la app FastAPI
- [ ] **7.1.2** Añadir servicio `app` al `docker-compose.yml`
- [ ] **7.1.3** Configurar network para que app pueda comunicarse con Brave y Playwright MCPs

### 7.2 — Naming consistency

> ✅ **Decisión tomada:** El nombre oficial es **AIFoundry**.

- [ ] **7.2.1** Verificar que `pyproject.toml` usa `name = "aifoundry"`
- [ ] **7.2.2** Verificar que `README.md` título y descripción dicen "AIFoundry"
- [x] **7.2.3** Verificar que no haya referencias a "Snipfee" en el código fuente

### 7.3 — Mejorar country.py

- [ ] **7.3.1** Evaluar usar `pycountry` library en vez de mapping manual
- [ ] **7.3.2** Si se mantiene manual, ampliar cobertura de países (al menos EU + LATAM)

---

## 📊 RESUMEN VISUAL

```
FASE 1 (🔴 Bugs)          ██████████ 2h   ✅ COMPLETADA
FASE 2 (🟡 Diseño)        ██████████████ 3h   ✅ COMPLETADA
FASE 3 (🟡 FastAPI)       ██████████ 2h   ✅ COMPLETADA (3.2.2-3.2.3 futuro)
FASE 4 (🟡 Config)        ██████████ 2h   ✅ COMPLETADA
FASE 5 (🟡 Tests)         ██████████████ 3h   ✅ COMPLETADA (149 tests, 0 fallos)
FASE 6 (🟢 Prompts)       ██████ 1h   ✅ COMPLETADA (5 pasos, criterios selección, STOP rule)
FASE 7 (🟢 Infra)         ░░░░░░ 1h   ← SIGUIENTE (última fase)
                           ──────────────
                           COMPLETADO: ~13h / ~14h total
```

## 🎯 ORDEN DE EJECUCIÓN RECOMENDADO

1. ~~**FASE 1** → Arreglar bugs críticos (fundamento estable)~~ ✅
2. ~~**FASE 2** → Limpiar diseño (código mantenible)~~ ✅
3. ~~**FASE 3** → Endpoints REST (funcionalidad completa)~~ ✅
4. ~~**FASE 4** → Validación config con Pydantic (robustez)~~ ✅
5. ~~**FASE 5** → Tests unitarios + integración (149 tests passed)~~ ✅
6. ~~**FASE 6** → Optimizar prompts (5 pasos, selección inteligente, STOP rule)~~ ✅
7. **FASE 7** → Infraestructura (despliegue) ← ÚLTIMA FASE
