# AIFoundry - Backend de AI Genérico

Backend de AI genérico en Python que soporta los 4 paradigmas de AI modernos usando LangChain, LangGraph, FastAPI y LiteLLM.

## 🎯 Paradigmas Soportados

| Paradigma | Descripción | Estado |
|-----------|-------------|--------|
| **1. LLM Workflow** | Chatbots, text generation | ⏳ Pendiente |
| **2. RAG** | Q&A con vector DB | ⏳ Pendiente |
| **3. AI Agent** | Autonomous action con tools | ✅ Implementado |
| **4. Multi-Agent** | Colaboración entre agentes | ⏳ Pendiente |

## 🛠 Stack Tecnológico

| Tecnología | Propósito |
|------------|-----------|
| **LangChain** | Orquestación LLMs, Agents |
| **LangGraph** | Runtime para agentes |
| **FastAPI** | API REST |
| **LiteLLM** | Multi-proveedor LLM |

---

## ✅ IMPLEMENTADO: LLM Factory (`core/models/`)

Singleton que proporciona el LLM base para todos los paradigmas.

```python
from aifoundry.app.core.models import get_llm

llm = get_llm()
response = await llm.ainvoke("Hola")
```

Configuración en `.env`:
```bash
LITELLM_API_BASE=https://api.inditex.com/litellm
LITELLM_API_KEY=sk-your-key
LITELLM_MODEL=bedrock/claude-sonnet-4
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=1000
```

---

## ✅ IMPLEMENTADO: Paradigma 3 - AI Agent (`core/agents/`)

> **📚 Documentación completa:** Ver **[docs/AGENTS.md](docs/AGENTS.md)** para guía detallada de cómo crear nuevos agentes.

> **⚠️ NO ELIMINAR:** El agente de ejemplo (`core/agents/example/`) sirve como referencia para crear nuevos agentes.

### Estructura de un Agent

```
aifoundry/app/core/agents/
├── __init__.py              # Export de agentes
└── example/                 # ⚠️ NO ELIMINAR - Agente de referencia
    ├── __init__.py
    ├── agent.py             # Clase ExampleAgent
    ├── tools.py             # get_tools() + @tool decorators
    └── prompts.py           # get_system_prompt() + get_user_prompt()
```

### Patrón de Agent (Resumen)

```python
# 1. tools.py - Herramientas con @tool
@tool
def mi_tool(param: str) -> str:
    """Docstring IMPORTANTE - el LLM lo lee para decidir cuándo usarla."""
    return resultado

def get_tools() -> List[BaseTool]:
    return [mi_tool, ...]

# 2. prompts.py - Funciones para prompts
def get_system_prompt() -> str:
    return "Eres un asistente..."

def get_user_prompt(message: str) -> str:
    return f"Pregunta: {message}"

# 3. agent.py - Clase del agente
class MiAgent:
    def __init__(self):
        self._agent = create_agent(
            model=get_llm(),
            tools=get_tools(),
            system_prompt=SystemMessage(content=get_system_prompt()),  # ← Aquí
        )
    
    async def invoke(self, message: str) -> str:
        response = await self._agent.ainvoke({
            "messages": [HumanMessage(content=get_user_prompt(message))]  # ← Solo HumanMessage
        })
        return response["messages"][-1].content
```

### Uso Rápido

```python
from aifoundry.app.core.agents import ExampleAgent

agent = ExampleAgent()
response = await agent.invoke("¿Qué hora es?")
print(response)  # "La hora actual es 15:08:22"
```

### Para crear un nuevo agente

1. Copia `core/agents/example/` como base
2. Modifica `tools.py`, `prompts.py`, `agent.py`
3. Exporta en `core/agents/__init__.py`
4. Ver **[docs/AGENTS.md](docs/AGENTS.md)** para guía completa

---

## 📁 Estructura del Proyecto

```
aifoundry/
├── app/
│   ├── config.py               # Settings (pydantic-settings)
│   ├── main.py                 # FastAPI entry point
│   │
│   ├── core/
│   │   ├── models/
│   │   │   └── llm.py          # ✅ LLM Factory (Singleton)
│   │   │
│   │   └── agents/             # ✅ Paradigma 3
│   │       └── example/        # Agent de ejemplo funcionando
│   │           ├── agent.py
│   │           ├── tools.py
│   │           └── prompts.py
│   │
│   ├── api/v1/                 # Endpoints (pendiente)
│   └── tools/                  # Tools comunes (pendiente)
│
├── scripts/
│   ├── test_litellm.py         # Test del LLM
│   └── test_agent.py           # Test del ExampleAgent
│
└── .env                        # Configuración
```

---

## 🚀 Instalación y Uso

```bash
# Setup
git clone https://github.com/user/aifoundry.git
cd aifoundry
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Configurar
cp .env.example .env
# Editar .env con credenciales

# Test LLM
PYTHONPATH=. python scripts/test_litellm.py

# Test Agent
PYTHONPATH=. python scripts/test_agent.py
```

---

## 📄 Licencia

MIT License
