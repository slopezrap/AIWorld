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

- [ ] **Mapear dependencias internas** del `ConfigurableAgent` actual:
  - Identificar los 5 bloques funcionales: memoria, tool calling, ejecución de fases, parsing de output, orquestación principal.
  - Documentar qué métodos llaman a qué otros para entender el acoplamiento.
- [ ] **Definir interfaces/contratos** (Protocol classes o ABCs) para cada módulo extraído:
  - `MemoryManager` — gestión de sesiones y mensajes
  - `ToolExecutor` — resolución y ejecución de tools (MCP + internas)
  - `PhaseRunner` — ejecución secuencial de fases
  - `OutputParser` — extracción de structured data del LLM
  - `AgentOrchestrator` — coordinación de todo lo anterior (el nuevo `agent.py` reducido)
- [ ] **Escribir tests del agente actual** (con LLM mockeado) ANTES de refactorizar, para tener red de seguridad:
  - Test de `chat()` con respuesta simple (sin tools)
  - Test de `chat()` con tool calling (mock de MCP)
  - Test de ejecución multi-fase
  - Test de memoria multi-turno
  - Test de cleanup de sesiones expiradas

### 1.2 Extracción del Módulo de Memoria (`memory.py`)

- [ ] Crear `aifoundry/app/core/agents/base/memory.py`
- [ ] Extraer de `agent.py`:
  - `conversation_memory: dict` → clase `ConversationMemoryManager`
  - `cleanup_expired_sessions()` → método de la clase
  - `_get_memory()` / `_add_to_memory()` → métodos de la clase
  - Toda la lógica de TTL y maxlen
- [ ] Definir interfaz abstracta `BaseMemoryManager` (Protocol):
  ```python
  class BaseMemoryManager(Protocol):
      async def get_messages(self, session_id: str) -> list[dict]
      async def add_message(self, session_id: str, role: str, content: str) -> None
      async def clear_session(self, session_id: str) -> None
      async def cleanup_expired(self) -> int  # retorna nº de sesiones eliminadas
  ```
- [ ] Implementar `InMemoryManager(BaseMemoryManager)` — comportamiento actual
- [ ] **Reemplazar `cleanup_expired_sessions()` en cada request** por un `asyncio` background task periódico (cada 60s) registrado en el `lifespan` de FastAPI
- [ ] Actualizar `agent.py` para inyectar `MemoryManager` en el constructor
- [ ] Verificar que los tests existentes siguen pasando

### 1.3 Extracción del Tool Executor (`tool_executor.py`)

- [ ] Crear `aifoundry/app/core/agents/base/tool_executor.py`
- [ ] Extraer de `agent.py`:
  - `_get_available_tools()` → resolución de tools desde config (MCP refs + internas)
  - `_execute_tool_call()` → ejecución de una tool individual
  - `_connect_mcp_and_get_tools()` → conexión a MCP servers
  - Mapping de herramientas internas (`simple_scrape_url`, `get_country_info`)
- [ ] Definir clase `ToolExecutor`:
  ```python
  class ToolExecutor:
      async def resolve_tools(self, tool_names: list[str]) -> list[ToolSchema]
      async def execute(self, tool_name: str, arguments: dict) -> ToolResult
      async def get_openai_tool_schemas(self, tool_names: list[str]) -> list[dict]
  ```
- [ ] **Implementar pool/cache de conexiones MCP** — en lugar de abrir/cerrar por cada request:
  - Cache de `ClientSession` por URL de MCP server
  - Reconexión automática si la sesión se cierra
  - Timeout configurable para conexiones MCP
- [ ] Hacer `max_iterations` configurable desde `config.json` (actualmente hardcoded a 20)
- [ ] Añadir **eventos/callbacks** en la ejecución de tools para preparar el streaming:
  ```python
  class ToolEvent:
      event_type: Literal["tool_start", "tool_result", "tool_error"]
      tool_name: str
      arguments: dict | None
      result: str | None
  ```
- [ ] Actualizar `agent.py` para usar `ToolExecutor` inyectado
- [ ] Tests unitarios del `ToolExecutor` con MCP mockeado

### 1.4 Extracción del Phase Runner (`phase_runner.py`)

- [ ] Crear `aifoundry/app/core/agents/base/phase_runner.py`
- [ ] Extraer de `agent.py`:
  - Toda la lógica del loop `for phase in phases` dentro de `chat()`
  - Construcción de prompts por fase (system prompt override, inyección de output schema)
  - Acumulación de resultados entre fases
- [ ] Definir clase `PhaseRunner`:
  ```python
  class PhaseRunner:
      def __init__(self, tool_executor: ToolExecutor, llm_client, output_parser: OutputParser)
      async def run_phases(self, phases: list[PhaseConfig], context: PhaseContext) -> PhaseResult
      async def run_single_phase(self, phase: PhaseConfig, context: PhaseContext) -> PhaseResult
  ```
- [ ] `PhaseContext` debe contener: messages previos, memoria de sesión, country, params, resultados de fases anteriores
- [ ] Añadir **eventos/callbacks por fase** para streaming:
  ```python
  class PhaseEvent:
      event_type: Literal["phase_start", "phase_complete", "thinking"]
      phase_id: str
      content: str | None
  ```
- [ ] Tests unitarios del `PhaseRunner`

### 1.5 Extracción del Output Parser (`output_parser.py`)

- [ ] Crear `aifoundry/app/core/agents/base/output_parser.py`
- [ ] Extraer de `agent.py`:
  - `_parse_structured_output()` — extracción de JSON del texto LLM
  - Lógica de bloques markdown (```json...```)
  - Validación contra el `output_schema` del config
  - Fallback cuando el LLM no devuelve JSON válido
- [ ] Definir clase `OutputParser`:
  ```python
  class OutputParser:
      def parse(self, raw_text: str, expected_schema: dict | None) -> ParsedOutput
      def extract_json_block(self, text: str) -> dict | None
      def validate_against_schema(self, data: dict, schema: dict) -> ValidationResult
  ```
- [ ] Tests unitarios con múltiples formatos de output del LLM (JSON limpio, markdown block, texto mixto, JSON inválido)

### 1.6 Agente Orquestador Simplificado (`agent.py` refactorizado)

- [ ] Refactorizar `ConfigurableAgent` para que solo orqueste:
  ```python
  class ConfigurableAgent:
      def __init__(self, config: AgentConfig, memory: BaseMemoryManager, 
                   tool_executor: ToolExecutor, phase_runner: PhaseRunner, 
                   output_parser: OutputParser)
      async def chat(self, query: str, session_id: str, ...) -> ChatResult
  ```
- [ ] El método `chat()` simplificado debería ser ~50 líneas máximo:
  1. Recuperar memoria de sesión
  2. Construir contexto
  3. Ejecutar fases vía `PhaseRunner`
  4. Parsear output vía `OutputParser`
  5. Guardar en memoria
  6. Retornar resultado
- [ ] Crear **factory function** `create_agent(config_path: str) -> ConfigurableAgent` que ensamble todas las dependencias
- [ ] Verificar que TODOS los tests (nuevos y existentes) pasan
- [ ] Actualizar los imports en `router.py`

### 1.7 Actualización de Documentación

- [ ] Actualizar `docs/AGENTS.md` con la nueva estructura modular
- [ ] Documentar las interfaces/protocolos para contribuidores
- [ ] Actualizar los diagramas de arquitectura si los hay

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

- [ ] Crear `aifoundry/app/core/agents/base/events.py`:
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

- [ ] Crear `aifoundry/app/core/agents/base/redis_memory.py`
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

- [ ] Crear `aifoundry/app/core/agents/base/sqlite_memory.py`
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

- [ ] Crear factory en `aifoundry/app/core/agents/base/memory.py`:
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
| Líneas en `agent.py` | ~400 | ~80 |
| Módulos en `base/` | 4 archivos | 8+ archivos |
| Test coverage del agente | 0% | >80% |
| Tiempo de respuesta API | Bloqueante (30s+) | Primer evento SSE <1s |
| Sesiones tras reinicio | Perdidas | Persistentes |
| Endpoints protegidos | 0 | Todos (excepto health) |