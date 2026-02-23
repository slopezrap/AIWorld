# AIFoundry Frontend — Arquitectura estilo Cline para Teams

> **Versión**: 1.2.0 (Corregida y mejorada)  
> **Fecha**: Febrero 2026  
> **Objetivo**: Definir la arquitectura de una aplicación frontend React inspirada en Cline, orientada a usuarios no técnicos, desplegable como Microsoft Teams Tab App.  
> **Nota**: Este documento distingue claramente entre lo que **ya existe** en el backend (✅) y lo que **hay que construir** (🔨).

---

## Tabla de Contenidos

1. [Análisis de Cline: Cómo funciona](#1-análisis-de-cline-cómo-funciona)
2. [Nuestra adaptación: De developer-tool a user-tool](#2-nuestra-adaptación-de-developer-tool-a-user-tool)
3. [Estado actual del backend](#3-estado-actual-del-backend)
4. [Arquitectura del sistema completo](#4-arquitectura-del-sistema-completo)
5. [Diseño del frontend](#5-diseño-del-frontend)
6. [Protocolo de streaming (a construir)](#6-protocolo-de-streaming-a-construir)
7. [Sistema de tools](#7-sistema-de-tools)
8. [User flows completos](#8-user-flows-completos)
9. [Integración con Microsoft Teams](#9-integración-con-microsoft-teams)
10. [Stack tecnológico](#10-stack-tecnológico)
11. [Estructura del proyecto frontend](#11-estructura-del-proyecto-frontend)
12. [API Contract: Backend ↔ Frontend](#12-api-contract-backend--frontend)
13. [MVP vs Future Work](#13-mvp-vs-future-work)

---

## 1. Análisis de Cline: Cómo funciona

### 1.1 Arquitectura interna de Cline

Cline es un agente AI que opera dentro de VS Code. Su poder reside en un **loop ReAct** (Reason → Act → Observe → Repeat) con estas piezas clave:

```
┌─────────────────────────────────────────────────────────┐
│                    CLINE ARCHITECTURE                    │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────┐  │
│  │  USER     │───▶│  AGENT   │───▶│  TOOL EXECUTOR   │  │
│  │  MESSAGE  │    │  (LLM)   │    │                  │  │
│  └──────────┘    └────┬─────┘    │  • read_file     │  │
│                       │          │  • write_to_file  │  │
│                       │          │  • execute_cmd    │  │
│                       ▼          │  • browser_action │  │
│                  ┌──────────┐    │  • search_files   │  │
│                  │ STREAMING│    │  • MCP tools      │  │
│                  │ RESPONSE │    └────────┬─────────┘  │
│                  │          │             │             │
│                  │ thinking │◀────────────┘             │
│                  │ tool_use │   resultado               │
│                  │ result   │                           │
│                  │ text     │                           │
│                  └──────────┘                           │
└─────────────────────────────────────────────────────────┘
```

### 1.2 Principios clave de Cline que queremos replicar

| Principio | Cómo lo hace Cline | Cómo lo adaptamos |
|-----------|--------------------|--------------------|
| **Tool calling visible** | Muestra cada tool call como bloque expandible en la UI | Igual: bloques visuales con icono, nombre, parámetros y resultado |
| **Streaming en tiempo real** | El usuario ve el pensamiento del agente mientras se genera | 🔨 **A construir**: endpoint SSE + callbacks de LangGraph |
| **Loop iterativo** | El agente usa una tool, ve el resultado, decide el siguiente paso | ✅ **Ya existe**: ScraperAgent con LangGraph ReAct |
| **MCP para tools externas** | Conecta tools remotas via Model Context Protocol | ✅ **Ya existe**: Brave Search y Playwright via MCP |
| **System prompt dinámico** | Cambia según el contexto y las tools disponibles | ✅ **Ya existe**: prompts dinámicos desde config.json |
| **Aprobación del usuario** | Algunas tools requieren click de "Approve" | 📋 Future: documentado pero no en MVP |
| **Plan Mode / Act Mode** | Primero planifica, luego ejecuta | Adaptado: el agente explica qué va a hacer antes de hacerlo |

### 1.3 Flujo de un mensaje en Cline

```
1. Usuario escribe mensaje
2. Se envía al LLM con: system prompt + historial + tools disponibles
3. LLM responde con streaming:
   a. <thinking> Razonamiento interno </thinking>
   b. <tool_use> { tool: "search", params: {...} } </tool_use>
4. Frontend muestra el bloque de tool en tiempo real
5. Backend ejecuta la tool
6. Resultado se inyecta en el contexto del LLM
7. LLM continúa razonando con el resultado
8. Repite 3-7 hasta que el LLM da respuesta final
9. Frontend muestra la respuesta completa
```

### 1.4 Qué hace especial a Cline vs un chatbot normal

1. **Transparencia total**: El usuario VE qué hace el agente, no solo el resultado final
2. **Tools como ciudadanos de primera clase**: No son funciones ocultas, se muestran visualmente
3. **Iteración visible**: Se ve cómo el agente corrige errores, reintenta, adapta su estrategia
4. **Control del usuario**: Puede pausar, aprobar, rechazar, redirigir
5. **Extensibilidad**: Añadir una tool nueva = añadir capacidades al agente sin cambiar código

---

## 2. Nuestra adaptación: De developer-tool a user-tool

### 2.1 Diferencia fundamental

| Aspecto | Cline (developers) | Nuestra app (usuarios) |
|---------|--------------------|-----------------------|
| Configurar agente | Editar archivos .json/.yaml | **Formularios guiados con validación** |
| Añadir tools | Configurar MCP servers manualmente | **Catálogo visual de tools, activar/desactivar con toggle** |
| Ver resultados | Texto en terminal/editor | **Cards visuales con datos estructurados, tablas, gráficos** |
| Escribir prompts | El usuario escribe prompts complejos | **Formularios con campos estructurados (provider, país) + texto libre opcional** |
| Contexto | El usuario gestiona el contexto | **El sistema gestiona el contexto automáticamente** |

### 2.2 Principio de diseño: "Guided AI"

Nuestra app sigue el principio de **"Guided AI"**: el usuario tiene el poder de un agente AI pero guiado por la interfaz para que no necesite conocimientos técnicos.

```
┌─────────────────────────────────────────────────────┐
│                  GUIDED AI SPECTRUM                  │
│                                                     │
│  Chatbot básico ◄──────────────────► Cline (devs)  │
│       │                                    │        │
│  Sin tools                          Tools raw       │
│  Sin transparencia                  Transparencia   │
│  Respuesta directa                  total           │
│                                                     │
│                    ▲                                │
│                    │                                │
│              NUESTRA APP                            │
│         Tools + Transparencia                       │
│         + UX guiada para usuarios                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 2.3 Concepto de "Asistente de dominio"

En vez de un agente genérico que el usuario tiene que configurar, ofrecemos **asistentes preconfigurados por dominio** que el usuario puede personalizar a través de formularios:

- ⚡ **Asistente de Electricidad**: "Busca precios y tarifas de luz por proveedor y país"
- 💰 **Asistente de Salarios**: "Investiga salarios en retail por empresa y país"
- 💬 **Asistente de Social**: "Analiza comentarios sobre personas específicas en redes sociales"
- 🆕 **Crear nuevo asistente**: Formulario guiado paso a paso (🔨 future)

---

## 3. Estado actual del backend

> ⚠️ **IMPORTANTE**: Esta sección documenta lo que **ya existe y funciona** en el backend. Las secciones posteriores describen lo que hay que construir encima.

### 3.1 API existente

El backend FastAPI actual expone estos endpoints (sin prefijo de versión):

| Método | Path | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Health check con info del modelo, MCP servers y agentes |
| `GET` | `/agents` | Lista de agentes descubiertos (escaneo de directorios) |
| `GET` | `/agents/{agent_name}/config` | Config.json completo de un agente |
| `POST` | `/agents/{agent_name}/run` | **Ejecutar agente** (síncrono, respuesta completa) |

### 3.2 Modelo de invocación actual

Los agentes se invocan con **parámetros estructurados**, NO con texto libre:

```python
# Request: POST /agents/electricity/run
{
    "provider": "Endesa",              # REQUERIDO: empresa/persona concreta
    "country_code": "ES",              # ISO 3166-1 alpha-2 (default: "ES")
    "query": null,                     # Opcional: si null, se genera automáticamente
    "thread_id": null,                 # Opcional: UUID para multi-turn
    "structured_output": false,        # Si true, devuelve datos Pydantic tipados
    "use_mcp": true,                   # Si true, usa herramientas MCP (Brave, Playwright)
    "disable_simple_scrape": false,    # Si true, fuerza uso de Playwright
    "max_retries": 3                   # Reintentos ante errores de red (1-10)
}

# Response:
{
    "status": "success",                          # "success" | "error"
    "output": "Texto completo del agente...",     # Output en texto libre (markdown)
    "messages_count": 12,                         # Mensajes en la conversación LangGraph
    "attempts": 1,                                # Intentos realizados
    "thread_id": "abc-123-uuid",                  # Thread ID para multi-turn
    "urls": ["https://endesa.com/tarifas", ...],  # URLs procesadas por el agente
    "query_es": "precio electricidad Endesa...",   # Query en español generada
    "query_final": "electricity price Endesa...",  # Query final usada (puede diferir)
    "used_playwright": true,                       # Si se usó Playwright MCP
    "has_structured_output": false,                # Si hay structured_response
    "structured_response": null                    # Objeto estructurado (si se pidió)
}
```

La query se genera automáticamente desde el `query_template` del config:
- Electricidad: `"precio electricidad {provider} {country_name} {date}"`
- Salarios: `"salario {provider} {country_name} retail"`
- Social: `"{person_name} {social_network} comentarios opiniones"`

> **⚠️ Nota sobre Social Comments**: El request solo tiene campo `provider`. Para social_comments, el frontend debe mapear `person_name` → `provider` y construir la `query` manualmente incluyendo la red social seleccionada (ver sección 5.2).

### 3.3 Agentes existentes y sus diferencias

Los 3 agentes comparten la clase `ScraperAgent` pero sus configs son significativamente diferentes:

#### Electricidad (`electricity/config.json`)
```json
{
    "product": "electricidad",
    "freshness": "pw",
    "query_template": "precio electricidad {provider} {country_name} {date}",
    "countries": {
        "ES": { "providers": ["Endesa", "Iberdrola", "Naturgy"], "language": "es" },
        "PT": { "providers": ["EDP", "Galp", "Endesa"], "language": "pt" },
        "FR": { "providers": ["EDF", "Engie", "TotalEnergies"], "language": "fr" }
    },
    "extraction_prompt": "Para electricidad, extrae TARIFAS y PRECIOS...",
    "validation_prompt": "Valida que los datos de electricidad..."
}
```

#### Salarios (`salary/config.json`)
```json
{
    "product": "salarios",
    "freshness": "py",
    "query_template": "salario {provider} {country_name} retail",
    "countries": {
        "ES": { "providers": ["Zara", "Mango", "El Corte Inglés"], "language": "es" },
        "PT": { "providers": ["Zara", "Primark", "Continente"], "language": "pt" },
        "FR": { "providers": ["Zara", "H&M", "Decathlon"], "language": "fr" }
    }
    // Sin extraction_prompt ni validation_prompt (usa defaults genéricos)
}
```

#### Social Comments (`social_comments/config.json`)
```json
{
    "product": "comentarios en redes sociales",
    "freshness": "py",
    "query_template": "\"{person_name}\" {social_network} comentarios",
    "countries": {
        "ES": { "language": "es" },
        "PT": { "language": "pt" },
        "FR": { "language": "fr" }
    },
    "social_networks": ["Instagram", "X", "Facebook", "LinkedIn", "TikTok"],
    "extraction_prompt": "REGLA CRÍTICA: Solo extrae datos de la persona EXACTA que se busca...",
    "validation_prompt": "VALIDACIÓN ESTRICTA DE IDENTIDAD: El nombre completo debe coincidir EXACTAMENTE..."
}
```

**⚠️ Diferencias clave entre agentes:**
- `electricity` y `salary` usan `providers` (empresas) por país
- `social_comments` usa `social_networks` (5 redes: Instagram, X, Facebook, LinkedIn, TikTok) y `{person_name}` como placeholder (entre comillas literales en el query_template)
- Solo `electricity` y `social_comments` tienen `extraction_prompt` y `validation_prompt` (los prompts reales son extensos, aquí se muestran abreviados)
- El campo `freshness` varía: `"pw"` (past week) para electricidad, `"py"` (past year) para el resto

### 3.4 Tools existentes

| Tool | Tipo | Descripción |
|------|------|-------------|
| `brave_search` | MCP (Docker) | Búsqueda web via Brave API. Puerto 8082, transport `streamable_http` |
| `playwright_*` | MCP (Docker) | Navegación web headless (navigate, click, fill, screenshot, evaluate). Puerto 8931, transport `streamable_http` |
| `simple_scrape_url` | Local (Python) | Scraping directo con httpx + BeautifulSoup + readability + markdownify. No requiere Docker |

### 3.5 Multi-turn existente

El backend **ya soporta conversaciones multi-turn** via `InMemorySaver` de LangGraph:
- Se pasa `thread_id` en el request para continuar una conversación
- El estado se mantiene **en memoria** (se pierde al reiniciar el servidor)
- El frontend debe guardar y reenviar el `thread_id` para follow-ups

### 3.6 LLM Configuration

- **Proxy**: LiteLLM (OpenAI-compatible)
- **Model default**: `gpt-4o-mini`
- **Params**: temperature 0.1, max_tokens 15000, timeout 120s
- **Multi-provider**: Soporta OpenAI, Anthropic, Bedrock, etc. via LiteLLM

---

## 4. Arquitectura del sistema completo

### 4.1 Diagrama general

```
┌─────────────────────────────────────────────────────────────────┐
│                        MICROSOFT TEAMS                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    TAB APP (iframe)                        │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │              REACT SPA (Vite + TS)                  │  │  │
│  │  │                                                     │  │  │
│  │  │  ┌──────────┐  ┌────────────────────────────────┐  │  │  │
│  │  │  │ Sidebar  │  │     Chat Panel                 │  │  │  │
│  │  │  │          │  │                                │  │  │  │
│  │  │  │ Agents   │  │  Form (provider, country)      │  │  │  │
│  │  │  │ Chats    │  │  Messages + Tool Blocks        │  │  │  │
│  │  │  │ Tools    │  │  Streaming text                │  │  │  │
│  │  │  │ Config   │  │  Structured results            │  │  │  │
│  │  │  │          │  │                                │  │  │  │
│  │  │  └──────────┘  │  ┌──────────────────────────┐  │  │  │  │
│  │  │                │  │ Input + Quick Actions     │  │  │  │  │
│  │  │                │  └──────────────────────────┘  │  │  │  │
│  │  │                └────────────────────────────────┘  │  │  │
│  │  └────────────────────────┬────────────────────────────┘  │  │
│  └───────────────────────────┼───────────────────────────────┘  │
└──────────────────────────────┼──────────────────────────────────┘
                               │
                     ┌─────────┴─────────┐
                     │   MVP: Polling    │
                     │   Target: SSE     │
                     └─────────┬─────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND                             │
│                                                                  │
│  ✅ Existente:                                                   │
│  ┌──────────────┐  ┌─────────────────┐  ┌───────────────────┐  │
│  │ GET /health  │  │ GET /agents     │  │ GET /agents/      │  │
│  │              │  │                 │  │  {name}/config    │  │
│  └──────────────┘  └─────────────────┘  └───────────────────┘  │
│  ┌────────────────────────────────┐                              │
│  │ POST /agents/{name}/run       │ ← Asíncrono (devuelve Job ID) │
│  └──────────────┬─────────────────┘                              │
│                 │                                                 │
│  🔨 A construir (MVP):                                           │
│  ┌────────────────────────────────┐                              │
│  │ GET /jobs/{job_id}            │ ← Estado y resultado final    │
│  └──────────────┬─────────────────┘                              │
│                 │                                                 │
│  🔨 A construir:                                                 │
│  ┌────────────────────────────────┐                              │
│  │ POST /agents/{name}/stream    │ ← SSE, con tool callbacks   │
│  └──────────────┬─────────────────┘                              │
│                 │                                                 │
│                 ▼                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              SCRAPER AGENT (LangGraph ReAct) ✅           │   │
│  │                                                           │   │
│  │  System Prompt ◄── config.json (dinámico)                │   │
│  │  Tools ◄── MCP Servers + simple_scrape_url local         │   │
│  │  LLM ◄── LiteLLM (gpt-4o-mini default)                  │   │
│  │  Memory ◄── PostgresSaver (thread_id) 🔨                 │   │
│  └──────────────┬────────────────────┬──────────────────────┘   │
│                 │                    │                            │
└─────────────────┼────────────────────┼────────────────────────────┘
                  │                    │
        ┌─────────▼──────┐   ┌────────▼────────┐   ┌───────────────┐
        │  Brave Search  │   │   Playwright    │   │   POSTGRESQL  │
        │  MCP Server    │   │   MCP Server    │   │   (Docker)    │
        │  Docker :8082  │   │   Docker :8931  │   │   :5432       │
        │ streamable_http│   │ streamable_http │   │ Job Store +   │
        └────────────────┘   └─────────────────┘   │ Checkpointer  │
                                                   └───────────────┘
```

### 4.2 Estrategia de implementación: 2 fases

#### Fase 1 — MVP (Polling Asíncrono)
Para evitar timeouts en Teams (llamadas >30s), implementamos un patrón de **Polling**:

```
1. [Frontend] POST /agents/electricity/run { ... }
   → Recibe: { job_id: "123", status: "pending" } (Respuesta inmediata)
2. [Frontend] Muestra loading state
3. [Frontend] Loop cada 2s: GET /jobs/123
   → Recibe: { status: "running", steps_completed: 2 }
4. [Backend]  Termina ejecución
5. [Frontend] GET /jobs/123
   → Recibe: { status: "completed", result: { ... } }
6. [Frontend] Renderiza resultado final
```

*Nota: Esto requiere adaptar el backend para ejecutar el agente en background (BackgroundTasks de FastAPI).*

#### Fase 2 — Target (SSE streaming)
Se crea un nuevo endpoint `/agents/{name}/stream` que emite eventos durante la ejecución:
```
1. [Frontend] POST /agents/electricity/stream { provider: "Endesa", country_code: "ES" }
2. [Backend]  → SSE: { type: "status", status: "thinking" }
3. [Backend]  → SSE: { type: "thinking", content: "Voy a buscar..." }
4. [Backend]  → SSE: { type: "tool_start", tool_name: "brave_search", params: {...} }
5. [Backend]  → SSE: { type: "tool_result", tool_name: "brave_search", result: {...} }
6. [Backend]  → SSE: { type: "tool_start", tool_name: "playwright_navigate", ... }
7. [Backend]  → SSE: { type: "tool_result", ... }
8. [Backend]  → SSE: { type: "text", content: "Los precios son..." }
9. [Backend]  → SSE: { type: "structured_data", data: {...} }
10. [Backend] → SSE: { type: "done", execution_time_seconds: 45.2 }
11. [Frontend] Renderiza todo en tiempo real
```

---

## 5. Diseño del frontend

### 5.1 Layout principal

```
┌────────────────────────────────────────────────────────────────┐
│  ┌──── 280px ────┐  ┌──────────── fluid ───────────────────┐  │
│  │                │  │                                      │  │
│  │   ┌────────┐   │  │  ┌─ Agent Header ─────────────────┐ │  │
│  │   │  LOGO  │   │  │  │ ⚡ Electricidad     ⚙️  •••    │ │  │
│  │   └────────┘   │  │  └────────────────────────────────┘ │  │
│  │                │  │                                      │  │
│  │  ─── AGENTS ── │  │  ┌─ Query Form ──────────────────┐  │  │
│  │  ● Electricidad │  │  │ Provider: [Endesa    ▼]       │  │  │
│  │  ○ Salarios    │  │  │ País:     [España    ▼]       │  │  │
│  │  ○ Social      │  │  │            [Ejecutar ▶️]       │  │  │
│  │                │  │  └────────────────────────────────┘  │  │
│  │  ─── CHATS ─── │  │                                      │  │
│  │  Chat 1        │  │  ┌─ Message Stream ───────────────┐ │  │
│  │  Chat 2        │  │  │                                │ │  │
│  │                │  │  │  🤖 ──────────────────────     │ │  │
│  │  ─── TOOLS ─── │  │  │  ▸ Pensando...                 │ │  │
│  │  🔍 Brave ✅   │  │  │    Voy a buscar tarifas de    │ │  │
│  │  🌐 Playwright✅│  │  │    Endesa en España            │ │  │
│  │  📄 Scraper ✅ │  │  │                                │ │  │
│  │                │  │  │  ┌─ 🔍 brave_search ─────────┐ │ │  │
│  │                │  │  │  │ "precio electricidad       │ │ │  │
│  │                │  │  │  │  Endesa España 2026-02"    │ │ │  │
│  │                │  │  │  │ ✅ 12 resultados           │ │ │  │
│  │                │  │  │  └────────────────────────────┘ │ │  │
│  │                │  │  │                                │ │  │
│  │                │  │  │  ┌─ 🌐 playwright_navigate ──┐ │ │  │
│  │                │  │  │  │ endesa.com/tarifas         │ │ │  │
│  │                │  │  │  │ ⏳ Extrayendo datos...     │ │ │  │
│  │                │  │  │  └────────────────────────────┘ │ │  │
│  │                │  │  │                                │ │  │
│  │                │  │  │  Tarifas Endesa España:         │ │  │
│  │                │  │  │                                │ │  │
│  │                │  │  │  ┌─ 📊 Datos estructurados ──┐ │ │  │
│  │                │  │  │  │ Tarifa  │ €/kWh  │ Tipo   │ │ │  │
│  │                │  │  │  │ One Luz │ 0.142  │ Fija   │ │ │  │
│  │                │  │  │  │ PVPC    │ 0.098  │ Regul. │ │ │  │
│  │                │  │  │  └────────────────────────────┘ │ │  │
│  │                │  │  └────────────────────────────────┘ │  │
│  │                │  │                                      │  │
│  │                │  │  ┌─ Follow-up Input ─────────────┐  │  │
│  │                │  │  │ Escribe para continuar...  [▶️] │  │  │
│  │                │  │  └──────────────────────────────┘  │  │
│  └────────────────┘  └──────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

### 5.2 Diferencia clave con v1.0 del doc: Formularios, no solo texto libre

El backend actual requiere **parámetros estructurados** (`provider`, `country_code`). Por tanto:

1. **Primera interacción**: El usuario rellena un formulario con los campos del agente seleccionado
2. **Follow-ups**: Texto libre que se envía con el mismo `thread_id` para multi-turn
3. **Quick Actions**: Botones predefinidos que rellenan el formulario automáticamente

Cada agente muestra un formulario diferente:

| Agente | Campos del formulario | Mapeo al backend |
|--------|----------------------|------------------|
| Electricidad | `provider` (dropdown: Endesa, Iberdrola, Naturgy...) + `country` (dropdown: ES, PT, FR) | Directo: `provider` → `provider`, `country` → `country_code` |
| Salarios | `provider` (dropdown: Zara, H&M, Mango...) + `country` (dropdown: ES, PT, FR) | Directo: `provider` → `provider`, `country` → `country_code` |
| Social Comments | `person_name` (text input) + `social_network` (dropdown: Instagram, X, Facebook, LinkedIn, TikTok) + `country` (dropdown: ES, PT, FR) | **Mapeo especial**: `person_name` → `provider`, y se construye `query` custom: `"\"{person_name}\" {social_network} comentarios"` |

> **⚠️ Mapeo Social Comments**: El backend no tiene campos `person_name` ni `social_network`. El frontend debe:
> 1. Enviar `person_name` como valor de `provider`
> 2. Construir el campo `query` manualmente combinando `person_name` + `social_network` + idioma del país
> 3. Ejemplo: `{ provider: "Juan García", country_code: "ES", query: "\"Juan García\" LinkedIn comentarios" }`

### 5.3 Componentes UI principales

#### A. `<Sidebar />`

```
Secciones:
├── Logo + Branding (Inditex/AIFoundry)
├── AgentList
│   ├── AgentItem (nombre, icono, estado activo)
│   └── + "Crear nuevo asistente" → abre wizard (🔨 future)
├── ChatHistory (en MVP: solo sesión actual, sin persistencia)
│   ├── ChatItem (título auto-generado, fecha)
│   └── + "Nueva consulta"
├── ToolsPanel (informativo)
│   ├── ToolItem (nombre, icono, estado: connected/disconnected)
│   │   ├── 🔍 Brave Search
│   │   ├── 🌐 Playwright
│   │   └── 📄 Simple Scraper
│   └── + "Añadir herramienta" (🔨 future)
└── Settings (tema, idioma)
```

#### B. `<ChatPanel />`

```
Secciones:
├── AgentHeader
│   ├── Icono + Nombre del agente activo
│   ├── Badge de estado (ready/thinking/working)
│   └── Menú de opciones (configurar, info)
├── QueryForm (primera interacción)
│   ├── Campos dinámicos según agente (provider, country, person_name, etc.)
│   ├── QuickActions (botones que pre-rellenan el form)
│   └── SubmitButton
├── MessageStream
│   ├── QuerySummary (resumen de lo que se buscó: "Endesa en España")
│   ├── AgentMessage
│   │   ├── ThinkingBlock (colapsable, fondo suave)
│   │   ├── ToolBlock[] (uno por cada tool call)
│   │   │   ├── ToolHeader (icono, nombre, estado: loading/success/error)
│   │   │   ├── ToolParams (parámetros enviados, colapsable)
│   │   │   └── ToolResult (resultado, colapsable)
│   │   ├── TextContent (markdown renderizado de output)
│   │   └── StructuredData (tabla/card de structured_data)
│   └── StreamingIndicator (dots animados, solo en Fase 2)
├── MetaInfo
│   ├── Execution time, steps count, model used
│   └── Thread ID (para debug)
└── FollowUpInput (texto libre + thread_id para multi-turn)
    ├── TextInput (multiline)
    └── SendButton
```

#### C. `<ToolBlock />` — El corazón visual estilo Cline

Este es el componente más importante. Replica la experiencia de Cline donde ves cada tool call:

```
┌─────────────────────────────────────────────┐
│ 🔍 brave_search                    ✅ 1.2s │
├─────────────────────────────────────────────┤
│ ▸ Parámetros                                │
│   query: "precio electricidad Endesa        │
│           España 2026-02-23"                │
│   freshness: "pw"                           │
├─────────────────────────────────────────────┤
│ ▸ Resultado                                 │
│   12 resultados encontrados                 │
│   1. endesa.com/tarifas - "Tarifas Endesa"  │
│   2. tarifaluzhora.es - "Precio luz hoy"   │
│   3. ...                                    │
└─────────────────────────────────────────────┘
```

**Nota sobre Fase 1 (MVP)**: En la fase síncrona, los ToolBlocks se construyen parseando el campo `output` del agente (que incluye menciones a las tools usadas en formato markdown). En Fase 2 (SSE), se construyen en tiempo real desde los eventos. Si el backend incluye `tool_calls[]` estructurado (ver Apéndice C.5), el parseo regex se vuelve innecesario.

Estados del ToolBlock:
- **⏳ Loading**: Animación de pulso (solo Fase 2 con streaming)
- **✅ Success**: Borde verde, resultado expandible
- **❌ Error**: Borde rojo, mensaje de error expandible
- **⚠️ Needs approval**: Botones "Aprobar" / "Rechazar" (📋 future)

#### D. `<AgentWizard />` — Crear nuevo asistente (🔨 future)

> **⚠️ Requiere**: Nuevo endpoint backend para crear agentes dinámicamente. El backend actual descubre agentes por escaneo de directorios.

Formulario paso a paso (stepper) para crear un agente sin tocar código:

```
Paso 1: Información básica
├── Nombre del asistente: [________________]
├── Descripción: [________________________]
├── Icono: [selector de iconos]
└── [Siguiente →]

Paso 2: Dominio y búsqueda
├── ¿Qué tipo de información busca?
│   ○ Precios / Tarifas (tipo electricity)
│   ○ Datos de empleo / Salarios (tipo salary)
│   ○ Opiniones / Comentarios (tipo social_comments)
│   ○ Personalizado
├── Template de búsqueda:
│   [se pre-rellena según tipo seleccionado]
│   Electricity: "precio electricidad {provider} {country_name} {date}"
│   Salary: "salario {provider} {country_name} retail"
│   Social: "{person_name} {social_network} comentarios opiniones"
├── Frescura de resultados:
│   ○ Última semana (pw)  ○ Último mes (pm)  ○ Último año (py)
└── [← Anterior] [Siguiente →]

Paso 3: Países y proveedores/fuentes
├── Países: [ES ✓] [FR ✓] [DE ☐] [+ Añadir]
├── Para cada país:
│   └── Si tipo precios/salarios: Proveedores [Añadir] [Añadir]
│   └── Si tipo social: Redes sociales [LinkedIn ✓] [Twitter ✓]
│   └── Idioma del país: [Español ▼]
└── [← Anterior] [Siguiente →]

Paso 4: Prompts de extracción (avanzado, opcional)
├── Instrucciones de extracción:
│   [textarea con prompt para extraction_prompt]
├── Instrucciones de validación:
│   [textarea con prompt para validation_prompt]
└── [← Anterior] [Siguiente →]

Paso 5: Revisión y creación
├── Preview del config.json generado
├── Test: ejecutar una consulta de prueba
└── [← Anterior] [Crear asistente ✓]
```

Internamente genera un `config.json` que se escribe via nuevo endpoint `POST /agents` o se guarda en disco.

#### E. `<ToolCatalog />` — Añadir herramientas (🔨 future)

> **⚠️ Requiere**: Nuevo endpoint backend para registro dinámico de MCP servers. Actualmente las URLs están en variables de entorno de `config.py`.

```
┌─────────────────────────────────────────────────┐
│  🔌 Herramientas conectadas                     │
├─────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐             │
│  │ 🔍 Brave     │  │ 🌐 Playwright│             │
│  │ Search       │  │              │             │
│  │ Búsqueda web │  │ Navega webs, │             │
│  │ Puerto 8082  │  │ extrae datos │             │
│  │              │  │ Puerto 8931  │             │
│  │ [Conectado ✅]│  │ [Conectado ✅]│             │
│  └──────────────┘  └──────────────┘             │
│                                                  │
│  ┌──────────────┐                               │
│  │ 📄 Simple    │                               │
│  │ Scraper      │                               │
│  │ Scraping     │                               │
│  │ local (BS4)  │                               │
│  │ [Activo ✅]  │                               │
│  └──────────────┘                               │
│                                                  │
│  🔨 Future:                                     │
│  ┌──────────────┐                               │
│  │ 🔗 Custom    │                               │
│  │ MCP Server   │                               │
│  │ [Configurar] │                               │
│  └──────────────┘                               │
└─────────────────────────────────────────────────┘
```

### 5.4 Diseño visual: Principios Inditex

Inspirado en la estética minimalista de Zara/Inditex:

```css
/* Design Tokens */
:root {
  /* Colores */
  --color-bg-primary: #FFFFFF;
  --color-bg-secondary: #F5F5F5;
  --color-bg-sidebar: #FAFAFA;
  --color-text-primary: #1A1A1A;
  --color-text-secondary: #666666;
  --color-text-tertiary: #999999;
  --color-accent: #000000;           /* Negro Inditex */
  --color-accent-hover: #333333;
  --color-success: #2D7D46;
  --color-error: #D32F2F;
  --color-warning: #F57C00;
  --color-border: #E5E5E5;
  --color-tool-bg: #F8F9FA;
  --color-thinking-bg: #FFF8E1;

  /* Dark mode */
  --color-dark-bg-primary: #1A1A1A;
  --color-dark-bg-secondary: #242424;
  --color-dark-bg-sidebar: #141414;
  --color-dark-text-primary: #F5F5F5;
  --color-dark-accent: #FFFFFF;

  /* Tipografía */
  --font-primary: 'Inter', -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.5rem;

  /* Espaciado */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;

  /* Bordes y sombras */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md: 0 2px 8px rgba(0,0,0,0.06);
  --shadow-lg: 0 4px 16px rgba(0,0,0,0.08);
}
```

Principios visuales:
- **Minimalismo**: Mucho espacio en blanco, pocos elementos por pantalla
- **Tipografía como protagonista**: Tipo grande, pesos claros, jerarquía nítida
- **Negro como acento**: El negro es el color de marca (como Zara)
- **Animaciones sutiles**: Transiciones suaves, sin exageraciones
- **Sin bordes gruesos**: Separaciones por espaciado y color de fondo

---

## 6. Protocolo de streaming (🔨 a construir)

> **⚠️ ESTADO**: El backend actual NO tiene streaming. El endpoint `POST /agents/{name}/run` es síncrono. Esta sección describe el endpoint **a construir** para Fase 2.

### 6.1 Implementación en backend

Para añadir streaming hay que:
1. Crear endpoint `POST /agents/{agent_name}/stream` con `StreamingResponse`
2. Usar **LangGraph callbacks** para interceptar eventos del agente
3. Emitir cada evento como SSE

```python
# Pseudo-código del endpoint a crear
from fastapi.responses import StreamingResponse

@router.post("/agents/{agent_name}/stream")
async def stream_agent(agent_name: str, request: AgentRunRequest):
    async def event_generator():
        agent = ScraperAgent(agent_name)
        async for event in agent.stream(request):
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### 6.2 Tipos de eventos SSE

```typescript
type EventType =
  | "thinking"        // Razonamiento del agente
  | "tool_start"      // Inicio de tool call
  | "tool_result"     // Resultado de tool call
  | "tool_error"      // Error en tool call
  | "text"            // Texto de respuesta (streaming)
  | "structured_data" // Datos estructurados (JSON)
  | "status"          // Cambio de estado
  | "error"           // Error general
  | "done";           // Fin del stream

interface DoneEvent {
  type: "done";
  content: {
    total_duration_ms: number;
    tools_used: number;
    steps_count: number;
    model_used: string;
    thread_id: string;
  };
}
```

### 6.3 Estrategia dual del frontend

El frontend soporta **ambos modos** (sync y stream):

```typescript
async function executeAgent(agentName: string, request: AgentRunRequest) {
  try {
    return await streamAgent(agentName, request);  // Fase 2
  } catch {
    return await runAgentSync(agentName, request);  // Fase 1 fallback
  }
}
```

---

## 7. Sistema de tools

### 7.1 Tools actuales (✅ existentes)

| Tool | Tipo | Descripción |
|------|------|-------------|
| `brave_search` | MCP Docker :8082 | Búsqueda web via Brave API, transport `streamable_http` |
| `playwright_*` | MCP Docker :8931 | Navegación headless (navigate, click, fill, screenshot, evaluate) |
| `simple_scrape_url` | Local Python | Scraping con httpx + BeautifulSoup + readability + markdownify |

### 7.2 Cómo se conectan al agente

En `tools.py`: `MultiServerMCPClient` carga tools MCP + `simple_scrape_url` local → se pasan a `create_agent` de LangGraph. URLs en `config.py` via env vars.

### 7.3 Registro dinámico (🔨 future)

Requiere modificar `tools.py` para aceptar URLs dinámicas o crear un registry service.

---

## 8. User flows completos

### 8.1 Flow: Primera vez

```
1. Usuario abre la app → pantalla de bienvenida
2. Elige asistente: [⚡ Electricidad] [💰 Salarios] [💬 Social]
3. Se abre formulario del agente seleccionado
4. Quick Actions: [Endesa en España] [Iberdrola en España] [EDF en Francia]
5. Click en Quick Action o rellena manualmente → Ejecutar
6. Loading (30-60s) → Resultado con tool blocks + datos
```

### 8.2 Flow: Ejecución (Fase 1 MVP - Polling)

```
1. Rellena form: Provider=Endesa, País=ES
2. POST /agents/electricity/run → Recibe { job_id: "abc-123", status: "queued" }
3. Skeleton loading: "🔍 Iniciando investigación..."
4. Loop Polling (cada 2s): GET /jobs/abc-123
   → Estado "running" ... sigue loading
   → Estado "completed" → Recibe payload completo
5. Parsea output → construye ToolBlocks
6. Renderiza markdown + tabla de datos
7. Muestra MetaInfo: "45.2s · 5 pasos · gpt-4o-mini"
```

### 8.3 Flow: Follow-up (multi-turn)

```
1. Escribe: "¿Y cuáles son las tarifas de Iberdrola?"
2. POST /agents/electricity/run { provider: "Iberdrola", country_code: "ES", thread_id: "abc-123" }
3. Agente tiene contexto previo → nuevo resultado debajo
```

### 8.4 Flow: Social Comments (formulario diferente)

```
1. Selecciona "Social Comments"
2. Form: Persona=[Juan García], Red=[LinkedIn], País=[ES]
3. POST /agents/social_comments/run { 
     provider: "Juan García", 
     country_code: "ES", 
     query: "\"Juan García\" LinkedIn comentarios" 
   }
4. Resultado con análisis de comentarios
```

---

## 9. Integración con Microsoft Teams

### 9.1 Estrategia

React SPA (Vite build) → empaquetada con Teams Toolkit → Personal Tab App dentro de Teams.

### 9.2 Pasos

1. Desarrollar como SPA standalone (`http://localhost:5173`)
2. Añadir `@microsoft/teams-js` SDK
3. Crear `manifest.json` de Teams (Personal Tab)
4. `vite build` → deploy estático (Azure Static Web Apps)
5. Registrar en Teams Admin

### 9.3 Consideraciones

- **Responsive**: ancho variable en Teams tab
- **Tema**: detectar light/dark/high-contrast via `microsoftTeams.getContext()`
- **SSO**: token de Teams para autenticación contra backend
- **Standalone first**: funciona 100% sin Teams

### 9.4 CORS (Cross-Origin Resource Sharing)

> **⚠️ CRÍTICO para desarrollo**: El frontend en Vite (`:5173`) y el backend FastAPI (`:8000`) están en orígenes distintos. Sin CORS configurado, **todas las peticiones del frontend serán bloqueadas por el navegador**.

**En desarrollo** se resuelve de dos formas complementarias:

1. **Proxy en Vite** (recomendado para desarrollo):
```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/health': 'http://localhost:8000',
      '/agents': 'http://localhost:8000',
      '/jobs': 'http://localhost:8000',
    }
  }
});
```

2. **CORS en FastAPI** (necesario para producción y Teams):
```python
# main.py — Añadir middleware CORS
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",          # Vite dev
        "https://*.azurestaticapps.net",  # Azure Static Web Apps
        "https://teams.microsoft.com",    # Teams
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

> **✅ Ya implementado**: El `main.py` del backend ya incluye middleware CORS con `allow_origins=["*"]`. Para producción, se recomienda restringir los orígenes a los dominios específicos listados arriba (Vite dev, Azure Static Web Apps, Teams).

---

## 10. Stack tecnológico

### 10.1 Frontend

| Tecnología | Propósito |
|-----------|-----------|
| React 18+ | Framework UI |
| TypeScript 5+ | Tipado estático |
| Vite 5+ | Bundler y dev server |
| Zustand 4+ | Estado global ligero |
| **TanStack Query (React Query) 5+** | **Server state, caché, polling automático** |
| React Router 6+ | Navegación SPA |
| react-markdown | Renderizar `output` del agente |
| lucide-react | Iconos minimalistas |
| @microsoft/teams-js | SDK Teams |
| CSS Modules | Estilos por componente |
| **Vitest + React Testing Library** | **Testing unitario y de componentes** |
| **Playwright** | **Testing E2E (reutiliza el que ya tenemos en Docker)** |

> **Decisión: Zustand + TanStack Query**: Zustand gestiona estado local de UI (sidebar, tema, agente activo). TanStack Query gestiona todo el server state (fetching, caché, polling de jobs, refetch automático). Esta separación es clave para evitar bugs de sincronización y simplificar el polling de `GET /jobs/{id}`.

### 10.2 Backend extensiones (Fase 2)

| Tecnología | Propósito |
|-----------|-----------|
| FastAPI StreamingResponse | SSE endpoint |
| LangGraph callbacks | Interceptar eventos del agente |

### 10.3 Infraestructura

- **Backend**: FastAPI :8000 (Stateless, escalable horizontalmente)
- **Base de Datos**: **PostgreSQL** :5432 (Persistencia unificada de Jobs, Memoria e Historial)
- **Tools**:
  - MCP Brave Docker :8082
  - MCP Playwright Docker :8931
- **LLM Proxy**: LiteLLM
- **Orquestación**: docker-compose.yml

> **✅ Arquitectura Simplificada**: Usamos una única base de datos (SQL) para todo: cola de trabajos, memoria del agente a corto plazo y persistencia a largo plazo. Esto simplifica el mantenimiento y despliegue en Azure/AWS.

---

## 11. Estructura del proyecto frontend

```
frontend/
├── public/
│   ├── favicon.ico
│   ├── manifest.json          # Teams manifest
│   ├── color.png              # Teams icon
│   └── outline.png
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppLayout.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Header.tsx
│   │   ├── chat/
│   │   │   ├── ChatPanel.tsx
│   │   │   ├── QueryForm.tsx      # Form dinámico por agente
│   │   │   ├── MessageStream.tsx
│   │   │   ├── AgentMessage.tsx
│   │   │   ├── ThinkingBlock.tsx
│   │   │   ├── ToolBlock.tsx      # Estilo Cline
│   │   │   ├── StructuredData.tsx
│   │   │   ├── MetaInfo.tsx
│   │   │   └── FollowUpInput.tsx
│   │   ├── agents/
│   │   │   ├── AgentList.tsx
│   │   │   └── AgentItem.tsx
│   │   ├── tools/
│   │   │   └── ToolsPanel.tsx
│   │   └── common/
│   │       ├── Button.tsx
│   │       ├── Badge.tsx
│   │       ├── Select.tsx
│   │       ├── Collapsible.tsx
│   │       ├── Table.tsx
│   │       ├── Spinner.tsx
│   │       └── MarkdownRenderer.tsx
│   ├── hooks/
│   │   ├── useAgent.ts
│   │   ├── useAgentRun.ts
│   │   ├── useSSE.ts             # Fase 2
│   │   └── useTeams.ts
│   ├── stores/
│   │   ├── chatStore.ts
│   │   ├── agentStore.ts
│   │   ├── jobStore.ts            # Tracking de jobs en polling
│   │   └── uiStore.ts
│   ├── services/
│   │   ├── api.ts
│   │   ├── agentService.ts       # GET /agents, /agents/{name}/config
│   │   ├── runService.ts         # POST /agents/{name}/run
│   │   ├── streamService.ts      # POST /agents/{name}/stream (Fase 2)
│   │   └── healthService.ts
│   ├── types/
│   │   ├── agent.ts
│   │   ├── chat.ts
│   │   ├── sse.ts
│   │   └── api.ts
│   ├── utils/
│   │   ├── parseToolCalls.ts     # Parsear output para tool mentions
│   │   ├── formatters.ts
│   │   └── constants.ts
│   └── styles/
│       ├── globals.css
│       ├── themes/
│       │   ├── light.css
│       │   └── dark.css
│       └── components/
│           ├── sidebar.module.css
│           ├── chat.module.css
│           └── toolblock.module.css
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

---

## 12. API Contract: Backend ↔ Frontend

### 12.1 Endpoints existentes (✅)

```yaml
GET /health
  → { status, version, llm_model, mcp_servers: { brave_search: url, playwright: url }, agents_available }

GET /agents
  → { agents: [{ name, product, countries, providers_by_country, has_extraction_prompt, has_validation_prompt }], total }

GET /agents/{agent_name}/config
  → Raw config.json del agente (sin transformar)

POST /agents/{agent_name}/run        # ← YA EXISTE, es SÍNCRONO
  Request: { provider (req), country_code, query, thread_id, structured_output, use_mcp, disable_simple_scrape, max_retries }
  Response: { status, output, messages_count, attempts, thread_id, urls, query_es, query_final, used_playwright, has_structured_output, structured_response }
```

> **⚠️ Nota**: El endpoint `/run` actual es **síncrono** (bloquea hasta que el agente termina, 30-90s). Para el MVP con polling se necesita convertirlo en asíncrono (ver 12.2).

### 12.2 Endpoints a construir (🔨)

**Para MVP (Polling):**
```yaml
# Convertir /run a asíncrono:
POST /agents/{agent_name}/run        # Modificar para devolver job_id inmediatamente
  Request: (mismo schema que actual)
  Response: { job_id: "uuid", status: "queued" }

GET /jobs/{job_id}                   # NUEVO: consultar estado del job
  Response: { 
    job_id: "uuid", 
    status: "queued" | "running" | "completed" | "failed",
    progress?: { steps_completed: number, current_step?: string },
    result?: AgentRunResponse | null,   # Solo si status="completed"
    error?: string | null               # Solo si status="failed"
  }
```

**Para Fase 2 (Streaming):**
```yaml
POST /agents/{agent_name}/stream    # SSE streaming
```

**Futuro (Gestión):**
```yaml
POST /agents                        # Crear agente
PUT /agents/{agent_name}            # Actualizar agente
DELETE /agents/{agent_name}         # Eliminar agente
GET /tools                          # Listar tools
POST /tools/mcp                     # Registrar MCP server
```

### 12.3 Tipos TypeScript del frontend

> **✅ SINCRONIZADO**: Estos tipos mapean exactamente a los schemas Pydantic de `aifoundry/app/api/schemas.py`.

```typescript
// ═══════════════════════════════════════════════
// REQUEST — Mapea a schemas.AgentRunRequest
// ═══════════════════════════════════════════════
interface AgentRunRequest {
  provider: string;                    // REQUERIDO: empresa o persona a investigar
  country_code?: string;               // default: "ES", ISO 3166-1 alpha-2
  query?: string | null;               // Si null, se genera desde query_template
  thread_id?: string | null;           // UUID para multi-turn
  structured_output?: boolean;         // default: false
  use_mcp?: boolean;                   // default: true — habilita Brave/Playwright
  disable_simple_scrape?: boolean;     // default: false — fuerza Playwright
  max_retries?: number;                // default: 3, rango: 1-10
}

// ═══════════════════════════════════════════════
// RESPONSE — Mapea a schemas.AgentRunResponse
// ═══════════════════════════════════════════════
interface AgentRunResponse {
  status: "success" | "error";         // Estado de la ejecución
  output: string;                      // Output del agente en markdown/texto libre
  messages_count: number;              // Nº de mensajes en la conversación LangGraph
  attempts: number;                    // Intentos realizados (por retries)
  thread_id: string;                   // Thread ID para follow-ups
  urls: string[];                      // URLs procesadas por el agente
  query_es: string;                    // Query en español generada
  query_final: string;                 // Query final usada (puede ser traducida)
  used_playwright: boolean;            // Si se usó Playwright MCP
  has_structured_output: boolean;      // Si hay structured_response
  structured_response: Record<string, unknown> | null;  // Datos Pydantic (si se pidió)
}

// ═══════════════════════════════════════════════
// AGENTES — Mapea a schemas.AgentInfo / AgentListResponse
// ═══════════════════════════════════════════════
interface AgentInfo {
  name: string;                        // Nombre del directorio (electricity, salary, etc.)
  product: string;                     // Tipo de producto (electricidad, salarios, etc.)
  countries: string[];                 // Códigos de país soportados
  providers_by_country: Record<string, string[]>;  // Providers por país
  has_extraction_prompt: boolean;
  has_validation_prompt: boolean;
}

interface AgentListResponse {
  agents: AgentInfo[];
  total: number;
}

// ═══════════════════════════════════════════════
// HEALTH — Mapea a schemas.HealthResponse
// ═══════════════════════════════════════════════
interface HealthResponse {
  status: string;
  version: string;
  llm_model: string;
  mcp_servers: Record<string, string>;  // { brave_search: url, playwright: url }
  agents_available: number;
}

// ═══════════════════════════════════════════════
// JOB POLLING (🔨 a construir)
// ═══════════════════════════════════════════════
interface JobStatus {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  progress?: { steps_completed: number; current_step?: string };
  result?: AgentRunResponse | null;
  error?: string | null;
}

// ═══════════════════════════════════════════════
// TIPOS INTERNOS DEL FRONTEND
// ═══════════════════════════════════════════════
interface Conversation {
  id: string;
  agent_name: string;
  thread_id: string | null;
  title: string;
  messages: Message[];
  created_at: string;
}

interface Message {
  id: string;
  role: "user" | "agent";
  content: MessageContent[];
  timestamp: string;
  meta?: {
    messages_count?: number;
    attempts?: number;
    urls?: string[];
    query_es?: string;
    query_final?: string;
    used_playwright?: boolean;
    thread_id?: string;
  };
}

type MessageContent =
  | { type: "query_summary"; provider: string; country: string; agent: string }
  | { type: "text"; text: string }
  | { type: "thinking"; text: string; collapsed: boolean }
  | { type: "tool_call"; tool: ToolCallInfo }
  | { type: "structured_data"; data: Record<string, unknown> }
  | { type: "error"; message: string };

interface ToolCallInfo {
  id: string;
  tool_name: string;
  icon: string;
  params: Record<string, unknown>;
  status: "running" | "success" | "error";
  result?: unknown;
  duration_ms?: number;
}
```

---

## 13. MVP vs Future Work

### 13.1 MVP (Fase 1 — Polling)

| Feature | Backend | Prioridad |
|---------|---------|-----------|
| Selector de agente | ✅ GET /agents | 🔴 P0 |
| Formulario dinámico por agente | ✅ GET /agents/{name}/config | 🔴 P0 |
| Infraestructura DB | 🔨 **PostgreSQL Container** | 🔴 P0 |
| Job Queue (Async execution) | 🔨 **BackgroundTasks + SQL** | 🔴 P0 |
| Endpoint Estado (Polling) | 🔨 **GET /jobs/{id}** | 🔴 P0 |
| Renderizar output (markdown) | ✅ output | 🔴 P0 |
| Tool blocks (de `tool_calls[]` o parseados de output) | 🔨 tool_calls[] en backend + Frontend | 🔴 P0 |
| Multi-turn con thread_id | ✅ thread_id | 🟡 P1 |
| Datos estructurados (tablas) | ✅ structured_data | 🟡 P1 |
| Quick Actions | Frontend only | 🟡 P1 |
| MetaInfo (tiempo, pasos, modelo) | ✅ response fields | 🟡 P1 |
| Panel de tools informativo | ✅ GET /health | 🟢 P2 |
| Tema claro/oscuro | Frontend only | 🟢 P2 |

### 13.2 Fase 2 — Streaming SSE

Requiere: `POST /agents/{name}/stream` + LangGraph callbacks. Habilita ToolBlocks en tiempo real, thinking blocks live, progress indicators.

### 13.3 Evolución / Roadmap Técnico

Estas características son críticas para el entorno corporativo y se abordarán tras el MVP:

#### 1. Autenticación y Seguridad (SSO Teams)
- **Integración Azure AD**: El frontend obtendrá el token de identidad de Teams (`microsoftTeams.authentication.getAuthToken`).
- **Validación Backend**: El backend validará el token JWT contra el tenant de Inditex.
- **Rbac**: Roles de usuario (Admin vs Viewer) para gestionar agentes.

#### 2. Auditoría y Analytics
- **Historial Avanzado**: Búsqueda full-text en conversaciones pasadas.
- **Costes**: Registro granular de tokens y costes por departamento/usuario.
- **Dashboard**: Visualización de uso en PowerBI conectado a PostgreSQL.

#### 3. Otras mejoras (v2.0+)
- **Human-in-the-loop**: SSE event `approval_required` + botones Aprobar/Rechazar.
- **Agent Wizard**: Crear agentes desde UI.
- **Exportación**: CSV, PDF, portapapeles.
- **Multi-idioma**: Soporte i18n completo.
- **Agentes programados**: Cron + notificaciones en el Activity Feed de Teams.

---

## Apéndice A: Comparativa con Cline

| Característica | Cline | AIFoundry App |
|---------------|-------|---------------|
| Loop ReAct | ✅ API LLM directa | ✅ LangGraph |
| Tool calls visibles | ✅ Bloques expandibles | ✅ ToolBlock component |
| Streaming | ✅ Del LLM | 🔨 Fase 2 (SSE) |
| MCP tools | ✅ Nativo | ✅ langchain-mcp-adapters |
| Aprobación | ✅ Approve/Reject | 📋 Future |
| Configuración | Archivos JSON | **Formularios guiados** |
| Target user | Developers | **Usuarios de negocio** |
| Despliegue | VS Code Extension | **Teams Tab App** |

## Apéndice B: Decisiones de diseño

- **SSE vs WebSocket**: SSE es unidireccional (suficiente), más simple, funciona con proxies corporativos
- **Zustand vs Redux**: Mínimo boilerplate, ~1KB, TypeScript-first, suficiente para nuestro caso
- **No Fluent UI**: Queremos estilo Inditex/Zara minimalista, no look Microsoft estándar
- **Vite vs Next.js**: SPA pura sin SSR, más fácil de empaquetar como Teams Tab
- **Formularios vs texto libre**: El backend requiere parámetros estructurados (provider, country_code), no interpreta texto libre


---

## Apéndice C: Detalles adicionales de implementación

### C.1 Error handling en el frontend

El frontend debe manejar estos escenarios:

| Escenario | Cómo detectarlo | Qué mostrar al usuario |
|-----------|-----------------|------------------------|
| Backend no disponible | `fetch` falla con `TypeError` / timeout | Banner: "No se puede conectar con el servidor. Verifica que esté activo en puerto 8000" |
| MCP server caído | Response con error mencionando MCP | ToolBlock en estado error: "La herramienta Brave Search no está disponible" |
| Agente tarda >60s | Timeout configurable en frontend | Mensaje: "La búsqueda está tardando más de lo normal. ¿Deseas cancelar?" con botón [Cancelar] |
| Agente devuelve error | `output` contiene error o HTTP 500 | Card de error con mensaje + botón [Reintentar] |
| Config de agente inválida | GET /agents/{name}/config devuelve 404 | Redirect a selector de agentes |
| Provider no válido | Validación en frontend antes de enviar | Form validation: "Selecciona un proveedor" |
| Rate limiting | HTTP 429 | Banner: "Demasiadas consultas. Espera X segundos" |

```typescript
// hooks/useAgentRun.ts — Error handling
const useAgentRun = () => {
  const [state, setState] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const run = async (agentName: string, request: AgentRunRequest) => {
    setState('loading');
    setError(null);
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(`/agents/${agentName}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        if (response.status === 429) throw new Error('RATE_LIMITED');
        if (response.status === 404) throw new Error('AGENT_NOT_FOUND');
        throw new Error(`HTTP_${response.status}`);
      }

      const data: AgentRunResponse = await response.json();
      setState('success');
      return data;
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        setState('idle'); // User cancelled
        return null;
      }
      setState('error');
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    }
  };

  const cancel = () => abortControllerRef.current?.abort();

  return { run, cancel, state, error };
};
```

### C.2 Loading states detallados (Fase 1 MVP)

Durante la ejecución síncrona (30-60s), el frontend muestra una experiencia rica de loading:

```
┌─────────────────────────────────────────────┐
│ 🔍 Investigando tarifas de Endesa en España │
│                                             │
│  ████████████░░░░░░░░  ~40s estimado       │
│                                             │
│  El agente está:                            │
│  ✅ Conectando con el servicio              │
│  ✅ Buscando información en la web          │
│  ⏳ Analizando resultados...                │
│  ○  Generando informe                      │
│                                             │
│  [Cancelar consulta]                        │
└─────────────────────────────────────────────┘
```

**Estrategia de loading por fase:**

| Fase | Mecanismo | Precisión |
|------|-----------|-----------|
| Fase 1 (síncrono) | Timers simulados (ver abajo) | ⚠️ Aproximada — no refleja estado real |
| Fase 1 (polling) | `GET /jobs/{id}` devuelve `progress.current_step` | ✅ Real — el backend reporta progreso |
| Fase 2 (SSE) | Eventos `tool_start`/`tool_result` en tiempo real | ✅ Exacta |

**Timers simulados (solo si se usa el endpoint síncrono sin polling):**
- 0-5s: "Conectando con el servicio"
- 5-15s: "Buscando información en la web"
- 15-35s: "Analizando resultados"
- 35s+: "Generando informe"

> **⚠️ Limitación**: Los timers no reflejan el estado real. Si el agente termina en 10s, el usuario verá "Buscando información..." aunque ya esté listo. Con el patrón polling (MVP target), esto se reemplaza por progreso real del backend.

### C.3 Responsive design

| Breakpoint | Layout | Sidebar |
|-----------|--------|---------|
| ≥1024px (desktop) | Sidebar 280px + Chat fluid | Visible fija |
| 768-1023px (tablet) | Sidebar colapsable + Chat fluid | Toggle con hamburger |
| <768px (mobile/Teams narrow) | Chat fullscreen | Drawer overlay |

```css
/* Responsive breakpoints */
@media (max-width: 1023px) {
  .sidebar { position: fixed; transform: translateX(-100%); z-index: 100; }
  .sidebar.open { transform: translateX(0); }
  .main { margin-left: 0; }
}

@media (max-width: 767px) {
  .query-form { flex-direction: column; }
  .quick-actions { flex-wrap: wrap; }
  .tool-block-params { display: none; }  /* Colapsar por defecto en móvil */
}
```

### C.4 Accesibilidad (a11y)

Requisitos mínimos:
- **ARIA labels** en todos los elementos interactivos
- **Keyboard navigation**: Tab order lógico, Enter para accionar, Escape para cerrar modales
- **Screen reader**: Tool blocks deben anunciar su estado ("Herramienta brave_search completada en 1.2 segundos")
- **Contraste**: Cumplir WCAG AA mínimo (4.5:1 para texto normal, 3:1 para texto grande)
- **Focus indicators**: Visible en todos los elementos interactivos
- **Skip to content**: Enlace oculto para saltar la sidebar

### C.5 Parseo de `output` para ToolBlocks (Fase 1)

> **⚠️ FRAGILIDAD CONOCIDA**: Este parseo con regex es inherentemente frágil porque depende del formato de texto que genere el LLM, que puede variar entre ejecuciones. Es una solución temporal para Fase 1.
>
> **📋 Recomendación para Fase 1.5**: Añadir un campo `tool_calls: ToolCall[]` estructurado al `AgentRunResponse` del backend. LangGraph ya tiene esta información internamente (cada nodo de tool produce eventos que se pueden capturar). Esto haría el frontend mucho más robusto sin depender de regex. Cambio estimado: ~50 líneas en `agent.py` + nuevo campo en `schemas.py`.

En Fase 1, el backend devuelve todo en `output` (markdown). El frontend debe **parsear** este texto para extraer menciones a tools y construir ToolBlocks:

```typescript
// utils/parseToolCalls.ts

interface ParsedResponse {
  thinking: string[];       // Bloques de razonamiento
  toolCalls: ToolCallInfo[]; // Tools detectadas
  textContent: string;       // Texto final (sin tool mentions)
}

function parseRawResponse(raw: string): ParsedResponse {
  const thinking: string[] = [];
  const toolCalls: ToolCallInfo[] = [];
  
  // Detectar patrones comunes del agente:
  // 1. "I'll use brave_search to..." → thinking
  // 2. "Using tool: brave_search" → tool_start
  // 3. "Search results: ..." → tool_result
  // 4. "Navigating to https://..." → playwright tool
  // 5. "Scraping content from..." → simple_scrape_url
  
  const toolPatterns = [
    { regex: /(?:Using|Calling|Invoking)\s+(?:tool:?\s+)?(brave_search|brave_web_search).*?(?:query|search)[:\s]+["']?([^"'\n]+)/gi, tool: 'brave_search' },
    { regex: /(?:Navigat|Visit|Open|Go to)(?:ing|ed)?\s+(?:to\s+)?(https?:\/\/[^\s\)]+)/gi, tool: 'playwright_navigate' },
    { regex: /(?:Scrap|Fetch|Download)(?:ing|ed)?\s+(?:content\s+)?(?:from\s+)?(https?:\/\/[^\s\)]+)/gi, tool: 'simple_scrape_url' },
  ];
  
  // Parse y construir ToolCallInfo objects
  for (const pattern of toolPatterns) {
    let match;
    while ((match = pattern.regex.exec(raw)) !== null) {
      toolCalls.push({
        id: `tc-${toolCalls.length}`,
        tool_name: pattern.tool,
        icon: getToolIcon(pattern.tool),
        params: { query: match[2] || match[1] },
        status: 'success',
      });
    }
  }
  
  return { thinking, toolCalls, textContent: raw };
}

function getToolIcon(toolName: string): string {
  const icons: Record<string, string> = {
    'brave_search': '🔍',
    'brave_web_search': '🔍',
    'playwright_navigate': '🌐',
    'playwright_click': '🖱️',
    'playwright_fill': '📝',
    'playwright_screenshot': '📸',
    'simple_scrape_url': '📄',
  };
  return icons[toolName] || '🔧';
}
```

### C.6 Configuración del frontend

```typescript
// utils/constants.ts
export const CONFIG = {
  // API
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  
  // Timeouts
  AGENT_RUN_TIMEOUT_MS: 120_000,  // 2 min (backend timeout es 120s)
  HEALTH_CHECK_INTERVAL_MS: 30_000,
  
  // UI
  SIDEBAR_WIDTH: 280,
  MAX_MESSAGES_IN_VIEW: 50,
  THINKING_BLOCK_DEFAULT_COLLAPSED: true,
  TOOL_PARAMS_DEFAULT_COLLAPSED: true,
  TOOL_RESULT_DEFAULT_COLLAPSED: false,
  
  // Loading simulation (Fase 1)
  LOADING_STEPS: [
    { delay: 0, message: 'Conectando con el servicio...' },
    { delay: 5000, message: 'Buscando información en la web...' },
    { delay: 15000, message: 'Analizando resultados...' },
    { delay: 35000, message: 'Generando informe...' },
  ],
};
```

---

## Apéndice D: Plan de Sprints

### Visión general

```
Sprint 0 (Setup)           → 1 semana
Sprint 1 (Core MVP)        → 2 semanas
Sprint 2 (Polish MVP)      → 1 semana
Sprint 3 (Streaming)       → 2 semanas
Sprint 4 (Testing/Quality) → en paralelo con 1-3
Sprint 5 (Teams + Extras)  → 1 semana
                            ─────────
Total estimado:              7 semanas
```

### Sprint 0 — Setup y scaffold (1 semana)

- [ ] Crear proyecto frontend con Vite + React + TypeScript
- [ ] Configurar ESLint, Prettier, tsconfig
- [ ] Instalar dependencias: zustand, react-router, react-markdown, lucide-react
- [ ] Crear estructura de carpetas (src/components, hooks, stores, services, types, utils, styles)
- [ ] Definir design tokens en `globals.css` (colores, tipografía, espaciado, sombras)
- [ ] Crear tema light y dark (`themes/light.css`, `themes/dark.css`)
- [ ] Configurar `vite.config.ts` con proxy al backend (`/agents` → `localhost:8000`)
- [ ] Crear `api.ts` (fetch wrapper con base URL y error handling)
- [ ] Crear tipos TypeScript (`types/agent.ts`, `types/chat.ts`, `types/api.ts`)
- [ ] Crear `healthService.ts` y verificar conexión con backend
- [ ] Crear `agentService.ts` (GET /agents, GET /agents/{name}/config)
- [ ] Crear `runService.ts` (POST /agents/{name}/run)
- [ ] Smoke test: conectar al backend real y ver que devuelve datos

### Sprint 1 — Core MVP funcional (2 semanas)

**Semana 1: Layout + Formularios**
- [ ] Componente `<AppLayout />` (sidebar + main panel)
- [ ] Componente `<Sidebar />` con secciones (agents, tools info)
- [ ] Componente `<AgentList />` + `<AgentItem />` con datos de GET /agents
- [ ] Store `agentStore.ts` (Zustand: agentes disponibles, agente activo)
- [ ] Componente `<Header />` (nombre agente, badge de estado)
- [ ] Componente `<ChatPanel />` (contenedor principal)
- [ ] Componente `<QueryForm />` con campos dinámicos:
  - [ ] Dropdown de providers (cargados desde config del agente)
  - [ ] Dropdown de países (cargados desde config del agente)
  - [ ] Input text para person_name (solo social_comments)
  - [ ] Dropdown de social_network (solo social_comments)
  - [ ] Botón Submit
- [ ] Quick Actions: botones predefinidos que pre-rellenan el form
- [ ] Validación del formulario antes de enviar

**Semana 2: Ejecución + Resultados**
- [ ] Hook `useAgentRun.ts` (ejecutar agente, manejar loading/error/success, cancel)
- [ ] Componente `<Spinner />` con loading state rico (pasos simulados)
- [ ] Componente `<AgentMessage />` (contenedor de respuesta)
- [ ] Componente `<MarkdownRenderer />` (renderizar output del agente)
- [ ] Utilidad `parseToolCalls.ts` (extraer tools del output)
- [ ] Componente `<ToolBlock />` (estilo Cline: header, params, result, estados)
- [ ] Componente `<Collapsible />` (para thinking/params/results)
- [ ] Componente `<StructuredData />` (tabla si structured_data existe)
- [ ] Componente `<MetaInfo />` (execution_time, steps_count, model_used)
- [ ] Store `chatStore.ts` (conversaciones en sesión, mensajes)
- [ ] Componente `<MessageStream />` (scroll automático, lista de mensajes)
- [ ] Test end-to-end: seleccionar agente → rellenar form → ejecutar → ver resultado

### Sprint 2 — Polish MVP (1 semana)

- [ ] Componente `<FollowUpInput />` (texto libre + thread_id para multi-turn)
- [ ] Hook `useAgent.ts` (cargar config, providers, countries del agente activo)
- [ ] Componente `<ToolsPanel />` en sidebar (info de tools conectadas desde /health)
- [ ] Componente `<Badge />` (estados: ready, working, error)
- [ ] Error handling completo (ver Apéndice C.1)
- [ ] Loading states detallados (ver Apéndice C.2)
- [ ] Responsive layout (ver Apéndice C.3): sidebar colapsable, mobile-friendly
- [ ] Tema claro/oscuro con toggle en sidebar
- [ ] Store `uiStore.ts` (sidebar abierta/cerrada, tema activo)
- [ ] Accesibilidad básica: ARIA labels, keyboard nav, focus indicators
- [ ] Pulir CSS: spacing, tipografía, animaciones sutiles
- [ ] Favicon, logo, branding Inditex
- [ ] README.md del frontend con instrucciones de setup y desarrollo
- [ ] Test completo de todos los flujos con los 3 agentes

### Sprint 3 — Streaming SSE (2 semanas)

**Semana 1: Backend**
- [ ] Crear endpoint `POST /agents/{agent_name}/stream` en FastAPI
- [ ] Implementar LangGraph callback handler para interceptar eventos
- [ ] Emitir SSE events: thinking, tool_start, tool_result, text, structured_data, done
- [ ] Mantener compatibilidad con endpoint `/run` existente
- [ ] Tests del endpoint de streaming

**Semana 2: Frontend**
- [ ] Crear `streamService.ts` (cliente SSE con fetch + ReadableStream)
- [ ] Hook `useSSE.ts` (parsear eventos, acumular en state)
- [ ] Actualizar `useAgentRun.ts` con estrategia dual (stream → fallback sync)
- [ ] `<ToolBlock />` en tiempo real: estado loading mientras ejecuta, success al terminar
- [ ] `<ThinkingBlock />` en tiempo real: texto que se acumula
- [ ] `<StreamingText />` para texto de respuesta que se escribe progresivamente
- [ ] Progress indicators reales (reemplazar timers simulados)
- [ ] Test end-to-end con streaming real

### Sprint 4 — Testing y Quality (incluido en paralelo)

> **Nota**: El testing se ejecuta en paralelo con los sprints anteriores, no como sprint separado. Se lista aquí para visibilidad.

- [ ] Configurar Vitest + React Testing Library
- [ ] Tests unitarios para `parseToolCalls.ts` (input/output conocidos)
- [ ] Tests unitarios para stores de Zustand (agentStore, chatStore, uiStore)
- [ ] Tests de componentes: `<QueryForm />`, `<ToolBlock />`, `<MarkdownRenderer />`
- [ ] Tests de integración: `useAgentRun` hook con mock de API
- [ ] Tests E2E con Playwright: flujo completo seleccionar agente → ejecutar → ver resultado
- [ ] Configurar CI (GitHub Actions) para ejecutar tests en cada PR

### Sprint 5 — Extras y Teams (1 semana)

- [ ] Instalar `@microsoft/teams-js`
- [ ] Hook `useTeams.ts` (detectar contexto Teams, tema, SSO token)
- [ ] Crear `manifest.json` de Teams
- [ ] Crear iconos Teams (color.png, outline.png)
- [ ] Adaptar tema al contexto de Teams (light/dark/high-contrast)
- [ ] Probar como Personal Tab en Teams Developer Portal
- [ ] Exportar conversación: copiar al portapapeles
- [ ] Exportar tabla como CSV
- [ ] Documentación final y cleanup del código

---

## Apéndice E: Checklist de validación pre-deploy

### Funcionalidad
- [ ] Los 3 agentes (electricity, salary, social_comments) funcionan correctamente
- [ ] Formularios dinámicos muestran los campos correctos por agente
- [ ] El resultado se renderiza con markdown + tool blocks
- [ ] Multi-turn funciona con thread_id
- [ ] Quick Actions pre-rellenan el formulario
- [ ] Cancel funciona durante ejecución
- [ ] Error handling muestra mensajes claros

### UI/UX
- [ ] Tema claro funciona correctamente
- [ ] Tema oscuro funciona correctamente
- [ ] Responsive en desktop (≥1024px)
- [ ] Responsive en tablet (768-1023px)
- [ ] Responsive en Teams tab (ancho variable)
- [ ] Animaciones suaves y no bloqueantes
- [ ] Scroll automático al recibir mensajes nuevos
- [ ] Tool blocks se colapsan/expanden correctamente

### Rendimiento
- [ ] Build de producción < 500KB gzipped
- [ ] First Contentful Paint < 1.5s
- [ ] No memory leaks en conversaciones largas
- [ ] AbortController cancela requests correctamente

### Accesibilidad
- [ ] ARIA labels en elementos interactivos
- [ ] Tab order lógico
- [ ] Contraste WCAG AA
- [ ] Focus indicators visibles

### Integración
- [ ] Conexión al backend en localhost funciona
- [ ] Conexión al backend en producción funciona
- [ ] Health check muestra estado de MCP servers
- [ ] Teams SDK detecta contexto correctamente
