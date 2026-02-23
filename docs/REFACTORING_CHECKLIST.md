# 🔧 Checklist de Refactoring — AIFoundry Backend

> **Versión:** 1.0.0  
> **Fecha:** 2026-02-23  
> **Contexto:** Este checklist detalla las 4 grandes áreas de refactoring identificadas en la auditoría técnica, diseñadas para alinear el backend con la propuesta de frontend (`FRONTEND_DESIGN_PROPOSAL.md`) y preparar el sistema para producción.

---

## Índice

1. [Refactorizar `agent.py`](#1-refactorizar-agentpy)
2. [Añadir Autenticación](#2-añadir-autenticación)
3. [Implementar SSE/Streaming](#3-implementar-ssestreaming)
4. [Memoria Persistente](#4-memoria-persistente)

---

## 1. Refactorizar `agent.py`

> **Objetivo:** Descomponer el monolito `ConfigurableAgent` (~400 líneas) en módulos cohesivos con responsabilidad única. Esto facilita testing, mantenimiento y la futura integración de streaming.

### 1.1 Análisis y Preparación

- [x] **Mapear dependencias internas** del `ScraperAgent` actual:
  - Identificar los 4 bloques funcionales: memoria, tool resolving, parsing de output, orquestación principal.
  - Documentar qué métodos llaman a qué otros para entender el acoplamiento.
- [x] **Definir interfaces/contratos** para cada módulo extraído:
  - `InMemoryManager` / `NullMemoryManager` — gestión de memoria conversacional
  - `ToolResolver` — resolución de tools (MCP + locales)
  - `OutputParser` — extracción de structured data y parsing de texto
  - `ScraperAgent` — orquestador (el nuevo `agent.py` reducido)
- [x] **Escribir tests del agente actual** (con LLM mockeado) ANTES de refactorizar (46 tests en `test_scraper_agent.py`):
  - Test de `run()` con respuesta simple (sin tools)
  - Test de `run()` con structured output nativo
  - Test de `run()` con structured output legacy (fallback)
  - Test de retry en error recuperable
  - Test de error no recuperable
  - Test de memoria conversacional (multi-turn)

### 1.2 Extracción del Módulo de Memoria (`memory.py`)

- [x] Crear `aifoundry/app/core/agents/scraper/memory.py`
- [x] Extraer de `agent.py`:
  - Checkpointer de LangGraph → clase `InMemoryManager`
  - Thread ID management → `generate_thread_id()`
  - History access → `get_history()`
  - Session clearing → `clear_session()`
- [x] Implementar `InMemoryManager` — con `MemorySaver` de LangGraph
- [x] Implementar `NullMemoryManager` — para agentes sin memoria
- [x] Actualizar `agent.py` para usar `InMemoryManager`/`NullMemoryManager`
- [x] Tests unitarios: 11 tests en `test_memory.py`
- [x] Verificar que todos los tests pasan (206 ✅)
- [ ] **Futuro:** Reemplazar cleanup por background task periódico en `lifespan`

### 1.3 Extracción del Tool Resolver (`tool_executor.py`)

- [x] Crear `aifoundry/app/core/agents/scraper/tool_executor.py`
- [x] Extraer de `agent.py`:
  - `get_mcp_configs()` → método interno de `ToolResolver`
  - `get_local_tools()` → método `_get_local_tools()`
  - Conexión MCP via `MultiServerMCPClient` → `_resolve_mcp_tools()`
  - Cleanup de MCP clients → `cleanup()`
- [x] Definir clase `ToolResolver`:
  ```python
  class ToolResolver:
      async def resolve_tools(self) -> list[BaseTool]
      async def cleanup() -> None
  ```
- [x] Manejo graceful de fallos MCP (continúa solo con tools locales)
- [x] Actualizar `agent.py` para usar `ToolResolver` inyectado
- [x] Tests unitarios: 15 tests en `test_tool_executor.py` con MCP mockeado
- [x] Verificar que todos los tests pasan (221 ✅)
- [ ] **Futuro:** Pool/cache de conexiones MCP
- [ ] **Futuro:** Eventos/callbacks en la ejecución de tools para streaming

### 1.4 Extracción del Phase Runner (`phase_runner.py`)

> **Nota:** El agente actual usa un flujo ReAct (no fases secuenciales), así que no se necesita un `PhaseRunner` separado. La lógica de retry y ejecución está en `ScraperAgent.run()`. Se reconsiderará si se implementa ejecución multi-fase.

- [ ] **Futuro:** Si se implementan fases secuenciales, extraer a `phase_runner.py`
- [ ] **Futuro:** Eventos/callbacks por fase para streaming

### 1.5 Extracción del Output Parser (`output_parser.py`)

- [x] Crear `aifoundry/app/core/agents/scraper/output_parser.py`
- [x] Extraer de `agent.py`:
  - `_convert_to_structured()` → `OutputParser.extract_structured()`
  - `parse_output()` → `OutputParser.parse_text()`
  - Lógica de structured output nativo vs legacy (fallback)
- [x] Definir clase `OutputParser`:
  ```python
  class OutputParser:
      async def extract_structured(result, output, llm, config) -> BaseModel | None
      def parse_text(output: str) -> dict
  ```
- [x] Tests unitarios: 9 tests en `test_output_parser.py`
- [x] Verificar que todos los tests pasan (230 ✅)

### 1.6 Agente Orquestador Simplificado (`agent.py` refactorizado)

- [x] `ScraperAgent` ahora orquesta 3 módulos:
  1. `InMemoryManager` / `NullMemoryManager` — gestión de memoria
  2. `ToolResolver` — resolución de tools (MCP + locales)
  3. `OutputParser` — structured output + text parsing
- [x] El constructor inyecta las 3 dependencias
- [x] `run()` delega a `OutputParser.extract_structured()` y `OutputParser.parse_text()`
- [x] `initialize()` delega a `ToolResolver.resolve_tools()`
- [x] `cleanup()` delega a `ToolResolver.cleanup()`
- [x] Verificar que TODOS los tests pasan (230 ✅)
- **Nota:** `agent.py` tiene ~607 líneas (incluyendo `AgentCallbackHandler` ~90 líneas, error helpers ~50 líneas, docstrings extensos). El código de orquestación real del `ScraperAgent` es ~250 líneas.

### 1.7 Actualización de Documentación

- [x] Actualizar `docs/REFACTORING_CHECKLIST.md` con el estado actual
- [ ] Actualizar `docs/AGENTS.md` con la nueva estructura modular
- [ ] Documentar las interfaces/protocolos para contribuidores

---

## 2. Añadir Autenticación

> **Objetivo:** Proteger los endpoints con API key, alineado con lo que el frontend necesitará. El `FRONTEND_DESIGN_PROPOSAL.md` asume comunicación directa backend↔frontend, por lo que la auth debe ser ligera pero segura.

### 2.1 Diseño

- [ ] **Elegir mecanismo:** API Key en header `X-API-Key` (simple, suficiente para Phase 1 del frontend)
  - Futuro: OAuth2/JWT para multi-usuario (Phase 2+)
- [ ] **Definir configuración:**
  ```env
  # .env
  API_KEYS=key1,key2,key3          # Lista de API keys válidas (comma-separated)
  AUTH_ENABLED=true                  # Toggle para desarrollo local
  ```
- [ ] **Definir qué endpoints proteger:**
  - `GET /api/health` → ❌ NO proteger (necesario para health checks de Docker/K8s)
  - `GET /api/agents` → ✅ Proteger
  - `GET /api/agents/{name}/config` → ✅ Proteger
  - `POST /api/agents/{name}/chat` → ✅ Proteger
  - `DELETE /api/agents/{name}/sessions/{id}` → ✅ Proteger
  - Futuro `GET /api/agents/{name}/stream` → ✅ Proteger

### 2.2 Implementación

- [ ] Añadir `api_keys` y `auth_enabled` a `config.py` (`Settings`):
  ```python
  api_keys: list[str] = []       # Si vacío, auth deshabilitada
  auth_enabled: bool = False     # Toggle explícito
  ```
- [ ] Crear `aifoundry/app/api/auth.py`:
  ```python
  from fastapi import Security, HTTPException, status
  from fastapi.security import APIKeyHeader
  
  api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
  
  async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
      if not settings.auth_enabled:
          return "development"
      if api_key not in settings.api_keys:
          raise HTTPException(status_code=401, detail="API key inválida o ausente")
      return api_key
  ```
- [ ] Aplicar como dependencia en `router.py`:
  ```python
  router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])
  ```
  - Excepto `/health` que debe estar fuera del router protegido o tener su propio router sin auth
- [ ] Actualizar `.env.example` con las nuevas variables
- [ ] Actualizar `docker-compose.yml` para pasar las variables de entorno

### 2.3 Testing

- [ ] Test: Request sin API key → 401
- [ ] Test: Request con API key inválida → 401
- [ ] Test: Request con API key válida → 200
- [ ] Test: `/health` sin API key → 200 (no protegido)
- [ ] Test: `auth_enabled=false` → todas las requests pasan sin key

### 2.4 Documentación

- [ ] Actualizar `README.md` con instrucciones de autenticación
- [ ] Documentar en la sección de API de `AGENTS.md`
- [ ] Añadir header `X-API-Key` a la documentación OpenAPI (FastAPI lo hará automáticamente via `APIKeyHeader`)

---

## 3. Implementar SSE/Streaming

> **Objetivo:** Reemplazar el endpoint síncrono `POST /chat` con un sistema de streaming basado en SSE (Server-Sent Events), alineado con el **Phase 2** del `FRONTEND_DESIGN_PROPOSAL.md`. Esto elimina el cuello de botella del request bloqueante y habilita la UX de "pensamiento en vivo" tipo Cline.

### 3.1 Diseño del Protocolo SSE

> Referencia: `FRONTEND_DESIGN_PROPOSAL.md` sección "Streaming Protocol"

- [ ] **Definir tipos de evento SSE:**
  ```
  event: thinking        → data: {"content": "Analizando la consulta..."}
  event: phase_start     → data: {"phase_id": "search", "description": "Buscando información"}
  event: tool_start      → data: {"tool": "brave_search", "arguments": {"query": "..."}}
  event: tool_result     → data: {"tool": "brave_search", "result": "...", "success": true}
  event: text            → data: {"content": "Fragmento de respuesta..."}  (token streaming)
  event: structured_data → data: {"schema": "ElectricityResponse", "data": {...}}
  event: phase_complete  → data: {"phase_id": "search", "summary": "..."}
  event: done            → data: {"metadata": {"duration_ms": 1234, "model": "gpt-4o-mini", ...}}
  event: error           → data: {"code": "LLM_ERROR", "message": "..."}
  ```
- [ ] **Definir schemas Pydantic** para cada tipo de evento en `aifoundry/app/api/schemas.py`:
  ```python
  class SSEEvent(BaseModel):
      event: str
      data: dict
  
  class ThinkingEvent(BaseModel): ...
  class ToolStartEvent(BaseModel): ...
  class ToolResultEvent(BaseModel): ...
  # etc.
  ```

### 3.2 Sistema de Eventos Interno

- [ ] Crear `aifoundry/app/core/agents/scraper/events.py`:
  - Definir `AgentEvent` (union type de todos los eventos posibles)
  - Definir `EventEmitter` — interfaz para emitir eventos durante la ejecución:
    ```python
    class EventEmitter(Protocol):
        async def emit(self, event: AgentEvent) -> None
    
    class AsyncQueueEmitter(EventEmitter):
        """Emite eventos a un asyncio.Queue para consumo por SSE."""
        def __init__(self):
            self.queue: asyncio.Queue[AgentEvent] = asyncio.Queue()
        
        async def emit(self, event: AgentEvent) -> None:
            await self.queue.put(event)
        
        async def events(self) -> AsyncGenerator[AgentEvent, None]:
            while True:
                event = await self.queue.get()
                if event.event == "done":
                    yield event
                    break
                yield event
    ```
- [ ] Integrar `EventEmitter` en los módulos refactorizados:
  - `ToolExecutor.execute()` → emite `tool_start` y `tool_result`
  - `PhaseRunner.run_single_phase()` → emite `phase_start`, `thinking`, `phase_complete`
  - `OutputParser.parse()` → emite `structured_data`
  - `ConfigurableAgent.chat()` → emite `done` o `error`

### 3.3 Endpoint SSE

- [ ] Crear nuevo endpoint `POST /api/agents/{name}/stream` en `router.py`:
  ```python
  from sse_starlette.sse import EventSourceResponse
  
  @router.post("/agents/{agent_name}/stream")
  async def stream_agent(agent_name: str, request: ChatRequest):
      emitter = AsyncQueueEmitter()
      
      # Lanzar ejecución del agente en background
      async def run_agent():
          try:
              await agent.chat(query=request.query, ..., event_emitter=emitter)
          except Exception as e:
              await emitter.emit(ErrorEvent(message=str(e)))
      
      asyncio.create_task(run_agent())
      
      # Devolver stream SSE
      async def event_generator():
          async for event in emitter.events():
              yield {"event": event.event, "data": event.model_dump_json()}
      
      return EventSourceResponse(event_generator())
  ```
- [ ] Añadir dependencia `sse-starlette` al `pyproject.toml`
- [ ] **Mantener el endpoint `/chat` síncrono** como fallback para clientes simples (scripts, testing)
- [ ] Implementar timeout global para el stream (ej: 5 minutos máximo)

### 3.4 Token Streaming del LLM

- [ ] Modificar `llm.py` para soportar streaming:
  ```python
  async def acompletion_stream(self, messages, **kwargs) -> AsyncGenerator[str, None]:
      response = await litellm.acompletion(messages=messages, stream=True, **kwargs)
      async for chunk in response:
          delta = chunk.choices[0].delta.content
          if delta:
              yield delta
  ```
- [ ] Integrar con `PhaseRunner` para emitir eventos `text` por cada chunk
- [ ] **Nota:** Cuando hay tool calling, el LLM no streama texto sino tool calls. Manejar ambos flujos.

### 3.5 Compatibilidad con FRONTEND_DESIGN_PROPOSAL.md

- [ ] Verificar que los nombres de eventos SSE coinciden con los esperados por el frontend:
  - `thinking`, `tool_start`, `tool_result`, `text`, `structured_data`, `done`
- [ ] El endpoint debe aceptar el mismo `ChatRequest` body que `/chat`
- [ ] El evento `done` debe incluir los mismos `metadata` que la respuesta síncrona actual
- [ ] Verificar CORS headers para SSE (`text/event-stream`)

### 3.6 Testing

- [ ] Test unitario: `AsyncQueueEmitter` emite y consume eventos correctamente
- [ ] Test de integración: `/stream` devuelve `Content-Type: text/event-stream`
- [ ] Test de integración: El stream emite al menos `thinking` → `done`
- [ ] Test de error: Si el agente falla, se emite evento `error` y el stream se cierra
- [ ] Test de timeout: Si el agente excede el timeout, se emite error y se cierra
- [ ] **Load test básico:** 10 requests concurrentes de streaming no crashean el servidor

### 3.7 Documentación

- [ ] Actualizar `FRONTEND_DESIGN_PROPOSAL.md` para reflejar el endpoint real (`/stream` en lugar de `/run`)
- [ ] Documentar el protocolo SSE en un nuevo `docs/STREAMING.md`
- [ ] Añadir ejemplos de consumo SSE con `curl` y `EventSource` (JS)

---

## 4. Memoria Persistente

> **Objetivo:** Reemplazar el `dict` en memoria por un almacenamiento persistente que sobreviva reinicios y soporte escalado horizontal. El `FRONTEND_DESIGN_PROPOSAL.md` asume sesiones multi-turno, por lo que la persistencia es crítica.

### 4.1 Evaluación de Opciones

- [ ] **Evaluar y decidir** entre las opciones:

  | Opción | Pros | Contras | Recomendada para |
  |--------|------|---------|-----------------|
  | **SQLite** | Sin infra extra, persistente, incluido en Python | No escala horizontal, lock en escritura | Desarrollo / Single instance |
  | **Redis** | Rápido, TTL nativo, escala horizontal | Requiere infra extra (Docker service) | Producción / Multi-instance |
  | **PostgreSQL** | Robusto, transaccional, ya estándar en empresas | Más complejo, overhead para K/V simple | Si ya existe en la infra |

  **Recomendación:** Implementar **Redis como primary** (producción) con **SQLite como fallback** (desarrollo sin Docker).

### 4.2 Interfaz Abstracta (ya definida en 1.2)

- [ ] Confirmar que `BaseMemoryManager` del refactoring del agente soporta las operaciones necesarias:
  ```python
  class BaseMemoryManager(Protocol):
      async def get_messages(self, session_id: str) -> list[dict]
      async def add_message(self, session_id: str, role: str, content: str) -> None
      async def clear_session(self, session_id: str) -> None
      async def cleanup_expired(self) -> int
      async def list_sessions(self, agent_id: str) -> list[SessionInfo]  # NUEVO
      async def get_session_metadata(self, session_id: str) -> SessionMetadata | None  # NUEVO
  ```
- [ ] Definir `SessionInfo` y `SessionMetadata`:
  ```python
  class SessionMetadata(BaseModel):
      session_id: str
      agent_id: str
      created_at: datetime
      last_active: datetime
      message_count: int
      ttl_minutes: int
  ```

### 4.3 Implementación Redis (`redis_memory.py`)

- [ ] Crear `aifoundry/app/core/agents/scraper/redis_memory.py`
- [ ] Implementar `RedisMemoryManager(BaseMemoryManager)`:
  - **Estructura de datos Redis:**
    ```
    session:{session_id}:messages  → LIST de JSON strings (cada mensaje)
    session:{session_id}:metadata  → HASH (agent_id, created_at, last_active, ttl)
    agent:{agent_id}:sessions      → SET de session_ids
    ```
  - TTL nativo de Redis en las keys de sesión
  - `LTRIM` para respetar `max_messages`
- [ ] Añadir dependencia `redis[hiredis]` al `pyproject.toml`
- [ ] Añadir configuración a `config.py`:
  ```python
  redis_url: str = "redis://localhost:6379/0"
  memory_backend: Literal["memory", "redis", "sqlite"] = "memory"
  ```
- [ ] Añadir servicio Redis al `docker-compose.yml`:
  ```yaml
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
  ```

### 4.4 Implementación SQLite (`sqlite_memory.py`)

- [ ] Crear `aifoundry/app/core/agents/scraper/sqlite_memory.py`
- [ ] Implementar `SQLiteMemoryManager(BaseMemoryManager)`:
  - **Schema:**
    ```sql
    CREATE TABLE sessions (
        session_id TEXT PRIMARY KEY,
        agent_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ttl_minutes INTEGER DEFAULT 30
    );
    CREATE TABLE messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL REFERENCES sessions(session_id),
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX idx_messages_session ON messages(session_id);
    ```
  - Usar `aiosqlite` para operaciones async
  - Cleanup de sesiones expiradas via `DELETE WHERE last_active + ttl < now()`
- [ ] Añadir dependencia `aiosqlite` al `pyproject.toml`
- [ ] DB file en ruta configurable: `sqlite_db_path: str = "data/memory.db"`

### 4.5 Factory de Memoria

- [ ] Crear factory en `aifoundry/app/core/agents/scraper/memory.py`:
  ```python
  def create_memory_manager(backend: str, config: Settings) -> BaseMemoryManager:
      match backend:
          case "memory":
              return InMemoryManager()
          case "redis":
              return RedisMemoryManager(redis_url=config.redis_url)
          case "sqlite":
              return SQLiteMemoryManager(db_path=config.sqlite_db_path)
          case _:
              raise ValueError(f"Backend de memoria no soportado: {backend}")
  ```
- [ ] Instanciar en el `lifespan` de `main.py` y compartir vía `app.state`
- [ ] Inyectar en los agentes al crearlos

### 4.6 Migración de Datos

- [ ] El `InMemoryManager` existente debe seguir funcionando sin cambios (backward compatible)
- [ ] Añadir script de migración `scripts/migrate_memory.py` (por si en futuro se cambia de backend)
- [ ] Documentar el proceso de cambio de backend

### 4.7 Background Tasks

- [ ] Registrar tarea periódica de cleanup en el `lifespan`:
  ```python
  async def periodic_cleanup(memory: BaseMemoryManager):
      while True:
          await asyncio.sleep(60)  # cada minuto
          cleaned = await memory.cleanup_expired()
          if cleaned > 0:
              logger.info(f"🧹 Cleaned {cleaned} expired sessions")
  ```
- [ ] La tarea debe cancelarse limpiamente en el shutdown

### 4.8 Testing

- [ ] Test unitario: `InMemoryManager` — CRUD de mensajes, TTL, cleanup
- [ ] Test unitario: `RedisMemoryManager` — usar `fakeredis` para mock
- [ ] Test unitario: `SQLiteMemoryManager` — usar DB temporal en `/tmp`
- [ ] Test de integración: Reiniciar servidor → las sesiones persisten (Redis/SQLite)
- [ ] Test de integración: Múltiples workers comparten la misma memoria (Redis)
- [ ] Test de concurrencia: Escrituras simultáneas no corrompen datos

### 4.9 Documentación

- [ ] Actualizar `README.md` con opciones de backend de memoria
- [ ] Actualizar `docker-compose.yml` documentation
- [ ] Documentar variables de entorno nuevas en `.env.example`
- [ ] Actualizar `FRONTEND_DESIGN_PROPOSAL.md` sección de sesiones para reflejar la persistencia

---

## 📋 Orden de Ejecución Recomendado

```
Fase 1 (Fundamentos):
  1.1-1.7  Refactorizar agent.py          ← Primero, porque todo lo demás depende de esto
  
Fase 2 (Seguridad + Persistencia, en paralelo):
  2.1-2.4  Autenticación                  ← Independiente, se puede hacer en paralelo
  4.1-4.9  Memoria Persistente            ← Depende del refactoring de memoria (1.2)
  
Fase 3 (Streaming):
  3.1-3.7  SSE/Streaming                  ← Depende del sistema de eventos (1.3, 1.4)
```

### Dependencias entre tareas:

```
[1. Refactoring agent.py]
    ├── [1.2 Memoria] ──────→ [4. Memoria Persistente]
    ├── [1.3 ToolExecutor] ──→ [3. SSE/Streaming (eventos de tools)]
    ├── [1.4 PhaseRunner] ───→ [3. SSE/Streaming (eventos de fases)]
    └── [1.6 Orquestador] ──→ [3. SSE/Streaming (endpoint)]

[2. Autenticación] ──────────→ (independiente, se aplica a todos los endpoints)
```

---

## 📊 Métricas de Éxito

| Métrica | Antes | Después |
|---------|-------|---------|
| Líneas en `agent.py` | ~400 | ~607 (orquestación ~250, callback ~90, helpers ~50, docs ~200) |
| Módulos en `base/` | 4 archivos | 8 archivos (`agent.py`, `memory.py`, `tool_executor.py`, `output_parser.py`, `config_schema.py`, `prompts.py`, `tools.py`, `__init__.py`) |
| Test coverage del agente | 0% | 230 tests (46 agent + 11 memory + 15 tool_executor + 9 output_parser + 149 otros) |
| Tiempo de respuesta API | Bloqueante (30s+) | Primer evento SSE <1s |
| Sesiones tras reinicio | Perdidas | Persistentes |
| Endpoints protegidos | 0 | Todos (excepto health) |