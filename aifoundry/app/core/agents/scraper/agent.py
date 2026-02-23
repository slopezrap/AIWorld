"""
ScraperAgent - Agente ReAct BASE para scraping web.

Agente genérico con soporte para:
- Tools locales (get_local_tools)
- Tools MCP (Brave Search, Playwright)
- Logging via logging (no print())
- Structured output nativo via response_format de create_agent (1 sola llamada LLM)
- Fallback a post-processing con with_structured_output() (2 llamadas LLM)
- Checkpointer para memoria conversacional (InMemorySaver)

Se usa directamente con un config.json por dominio (salary, electricity, etc).
No requiere subclases — cada dominio solo necesita su config.json.

Nota sobre system_prompt:
    create_agent acepta `system_prompt=` pero es ESTÁTICO (se fija al crear el agente).
    Nuestro prompt es DINÁMICO (cambia por país/producto/provider en cada run()),
    así que lo pasamos como SystemMessage en los messages de cada invocación.
    Esto está documentado como patrón válido en la API oficial.
"""

import logging
import re
import uuid
import warnings
from typing import Optional, List, Dict, Type

from langchain_core.messages import HumanMessage, SystemMessage
from langchain.agents import create_agent
from langchain_core.tools import BaseTool
from langchain_core.callbacks import BaseCallbackHandler
from pydantic import BaseModel

from aifoundry.app.core.models.llm import get_llm
from aifoundry.app.core.agents.scraper.prompts import get_system_prompt
from aifoundry.app.core.agents.scraper.memory import InMemoryManager, NullMemoryManager
from aifoundry.app.core.agents.scraper.tool_executor import ToolResolver
from aifoundry.app.core.agents.scraper.output_parser import OutputParser

logger = logging.getLogger(__name__)


# =============================================================================
# CALLBACK HANDLER
# =============================================================================

class AgentCallbackHandler(BaseCallbackHandler):
    """
    Callback handler para logging del flujo del agente en tiempo real.

    Muestra los pasos del flujo:
    - PASO 0-2: Análisis y construcción de query
    - PASO 3: Búsqueda web (Brave)
    - PASO 4: Scraping simple
    - PASO 5: Playwright
    - PASO 6-7: Extracción y validación
    """

    # Mapeo de tool name → (paso, emoji + descripción)
    _TOOL_TO_STEP: Dict[str, tuple] = {
        "brave_web_search": ("3", "🔍 BÚSQUEDA WEB"),
        "simple_scrape_url": ("4", "📄 SCRAPING SIMPLE"),
        "browser_navigate": ("5", "🎭 PLAYWRIGHT"),
        "browser_snapshot": ("5", "🎭 PLAYWRIGHT"),
        "browser_click": ("5", "🎭 PLAYWRIGHT"),
        "browser_type": ("5", "🎭 PLAYWRIGHT"),
    }

    def __init__(self, agent_name: str = "BASE"):
        self.agent_name = agent_name
        self._first_llm = True
        self._current_step: Optional[str] = None
        self._logger = logging.getLogger(f"{__name__}.AgentCallback.{agent_name}")

    def _log_step_header(self, step_num: str, step_name: str) -> None:
        """Loguea header de paso si es diferente al actual."""
        if self._current_step != step_num:
            self._current_step = step_num
            self._logger.info("═" * 50)
            self._logger.info("  PASO %s: %s", step_num, step_name)
            self._logger.info("═" * 50)

    def on_llm_start(self, serialized, prompts, **kwargs) -> None:
        if self._first_llm:
            self._first_llm = False
            self._log_step_header("0-2", "📋 ANÁLISIS Y CONSTRUCCIÓN DE QUERY")
        self._logger.info("🤖 AGENT %s - LLM thinking...", self.agent_name)

    def on_llm_end(self, response, **kwargs) -> None:
        pass

    def on_tool_start(self, serialized, input_str, **kwargs) -> None:
        tool_name = serialized.get("name", "unknown")

        if tool_name in self._TOOL_TO_STEP:
            step_num, step_name = self._TOOL_TO_STEP[tool_name]
            self._log_step_header(step_num, step_name)

        truncated = input_str[:200] + "..." if len(input_str) > 200 else input_str
        self._logger.info("🔧 AGENT %s TOOL: %s | INPUT: %s", self.agent_name, tool_name, truncated)

    def on_tool_end(self, output, name: str = "", **kwargs) -> None:
        output_str = str(output)

        # Para brave_web_search, mostrar URLs encontradas
        if "brave" in name.lower() or "url" in output_str.lower()[:50]:
            urls = re.findall(r'"url":\s*"([^"]+)"', output_str)
            if urls:
                self._logger.info("   URLs encontradas (%d):", len(urls))
                for i, url in enumerate(urls[:10], 1):
                    self._logger.info("     %d. %s", i, url)
                return

        truncated = output_str[:500] + "..." if len(output_str) > 500 else output_str
        self._logger.info("   OUTPUT: %s", truncated)

    def on_tool_error(self, error, **kwargs) -> None:
        self._logger.error("   ❌ AGENT %s ERROR: %s", self.agent_name, error)

    def on_agent_action(self, action, **kwargs) -> None:
        pass  # Ya se muestra en on_tool_start

    def on_agent_finish(self, finish, **kwargs) -> None:
        self._log_step_header("6-7", "📊 EXTRACCIÓN Y VALIDACIÓN")
        self._logger.info("✅ AGENT %s FINISHED", self.agent_name)




# =============================================================================
# RECOVERABLE ERRORS
# =============================================================================

_RECOVERABLE_PATTERNS = (
    "err_http2_protocol_error",
    "net::err_",
    "page.goto:",
    "timeout",
    "connection refused",
    "connection reset",
    "ssl_error",
    "certificate",
    "name not resolved",
    "### error",
)

# Errores que indican "sin datos" pero NO son fallos de red
# No deben causar retry — se devuelven como resultado parcial/vacío
_NO_DATA_PATTERNS = (
    "no web results",
    "no results found",
)


def _is_recoverable_error(text: str) -> bool:
    """Verifica si el texto contiene un error de red recuperable."""
    if not text:
        return False
    text_lower = text.lower()
    return any(p in text_lower for p in _RECOVERABLE_PATTERNS)


def _is_no_data_error(text: str) -> bool:
    """Verifica si el error indica simplemente que no se encontraron datos."""
    if not text:
        return False
    text_lower = text.lower()
    return any(p in text_lower for p in _NO_DATA_PATTERNS)


def _extract_failed_url(text: str) -> Optional[str]:
    """Extrae la primera URL de un texto de error."""
    match = re.search(r'https?://[^\s\)\"\'`\]<>]+', text)
    return match.group().rstrip(".,;:") if match else None


def _tool_error_handler(error: Exception) -> str:
    """
    Handler para errores de tools MCP.

    Devuelve un mensaje amigable al LLM para que pueda decidir
    qué hacer (cambiar query, continuar con datos existentes, etc.)
    en vez de crashear todo el agente.
    """
    error_str = str(error)
    if _is_no_data_error(error_str):
        return (
            "No se encontraron resultados web para esta consulta. "
            "Intenta con una query diferente o continúa con los datos que ya tienes."
        )
    # Para otros errores, devolver el mensaje de error al LLM
    return f"Error en herramienta: {error_str[:500]}"


# =============================================================================
# SCRAPER AGENT
# =============================================================================

class ScraperAgent:
    """
    Agente ReAct BASE para scraping web.

    Soporta:
    - Tools locales (scraper, etc)
    - Tools MCP (Brave Search, Playwright)
    - Logging via callbacks
    - Structured output via with_structured_output()
    - Checkpointer con InMemorySaver para memoria conversacional

    Uso como context manager (recomendado):
        async with ScraperAgent() as agent:
            result = await agent.run(config)

    Uso con salida estructurada nativa (1 sola llamada LLM — RECOMENDADO):
        async with ScraperAgent(response_model=SalaryResponse) as agent:
            result = await agent.run(config)
            # result["structured_response"] → objeto Pydantic SalaryResponse

    Uso con salida estructurada por post-procesamiento (2 llamadas LLM — LEGACY):
        async with ScraperAgent(structured_output=True) as agent:
            result = await agent.run(config)
            # result["structured_response"] → objeto Pydantic (inferido del product)

    Uso con memoria multi-turn:
        async with ScraperAgent(use_memory=True) as agent:
            r1 = await agent.run(config1)  # El agente recuerda esto...
            r2 = await agent.run(config2)  # ...cuando procesa esto
            history = agent.get_history()
    """

    def __init__(
        self,
        tools: Optional[List[BaseTool]] = None,
        use_mcp: bool = True,
        disable_simple_scrape: bool = False,
        verbose: bool = True,
        use_memory: bool = True,
        structured_output: bool = False,
        response_model: Optional[Type[BaseModel]] = None,
        agent_name: Optional[str] = None,
    ):
        """
        Inicializa el agente.

        Args:
            tools: Lista de tools locales. Si None, usa get_local_tools().
            use_mcp: Si cargar tools MCP (Brave, Playwright). Default True.
            disable_simple_scrape: Si True, no incluye simple_scrape_url (fuerza Playwright).
            verbose: Si True, muestra logs del flujo en tiempo real.
            use_memory: Si True, usa InMemorySaver para persistir conversaciones.
            structured_output: Si True, fuerza salida estructurada por post-procesamiento
                (2 llamadas LLM). Inferir schema del product type. LEGACY — preferir
                response_model.
            response_model: Clase Pydantic para structured output NATIVO via
                response_format de create_agent. Se resuelve en 1 sola pasada.
                Si se pasa, tiene prioridad sobre structured_output=True.
            agent_name: Nombre del agente para debugging/tracing en LangGraph.
        """
        # Deprecation warning para structured_output=True sin response_model
        if structured_output and response_model is None:
            warnings.warn(
                "structured_output=True está DEPRECATED y causa una segunda llamada LLM "
                "innecesaria. Usa response_model=TuModeloPydantic en su lugar para "
                "structured output nativo en 1 sola pasada. Ejemplo:\n"
                "  ScraperAgent(response_model=SalaryResponse)\n"
                "Ver aifoundry/app/schemas/agent_responses.py para los modelos disponibles.",
                DeprecationWarning,
                stacklevel=2,
            )

        self.llm = get_llm()
        self._verbose = verbose
        self._use_memory = use_memory
        self._structured_output = structured_output
        self._response_model = response_model
        self._agent_name = agent_name
        self._use_mcp = use_mcp

        # Memory manager (abstrae el checkpointer de LangGraph)
        self._memory_manager = InMemoryManager() if use_memory else NullMemoryManager()
        self._checkpointer = self._memory_manager.get_checkpointer()

        # Thread ID estable para toda la vida del agente
        self._thread_id: str = self._memory_manager.generate_thread_id()

        # Callback para logging
        self._callbacks = [AgentCallbackHandler()] if verbose else []

        # Tool resolver (carga tools locales + MCP)
        self._tool_resolver = ToolResolver(
            use_mcp=use_mcp,
            disable_simple_scrape=disable_simple_scrape,
            custom_tools=tools,
        )

        # Output parser (structured output + text parsing)
        self._output_parser = OutputParser(
            response_model=response_model,
            use_structured_output=structured_output,
        )

        # Estado interno — se pobla en initialize()
        self._all_tools: Optional[List[BaseTool]] = None
        self._agent = None

    # -------------------------------------------------------------------------
    # Context manager
    # -------------------------------------------------------------------------

    async def __aenter__(self):
        """Context manager async — inicializa el agente."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager async — libera recursos."""
        await self.cleanup()

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def initialize(self) -> None:
        """
        Inicializa el agente UNA vez: carga tools (locales + MCP) y crea el
        agente ReAct con checkpointer.

        Es idempotente — si ya está inicializado, no hace nada.
        """
        if self._agent is not None:
            return

        # Resolver tools (locales + MCP) via ToolResolver
        self._all_tools = await self._tool_resolver.resolve_tools()

        # Construir kwargs para create_agent
        agent_kwargs: Dict = {
            "model": self.llm,
            "tools": self._all_tools,
            "checkpointer": self._checkpointer,
        }

        # response_format nativo — structured output en 1 sola pasada
        if self._response_model is not None:
            agent_kwargs["response_format"] = self._response_model
            logger.info(
                f"Using native response_format: {self._response_model.__name__}"
            )

        # Nombre del agente para debugging/tracing
        if self._agent_name:
            agent_kwargs["name"] = self._agent_name

        # Crear el agente UNA vez con checkpointer
        self._agent = create_agent(**agent_kwargs)

        logger.info(
            f"Agent initialized with {len(self._all_tools)} tools "
            f"(memory={'ON' if self._use_memory else 'OFF'}, "
            f"response_format={'native' if self._response_model else 'legacy' if self._structured_output else 'none'}, "
            f"thread={self._thread_id[:8]}...)"
        )

    async def cleanup(self) -> None:
        """Libera recursos (MCP client, agente)."""
        await self._tool_resolver.cleanup()
        self._agent = None
        self._all_tools = None

    # -------------------------------------------------------------------------
    # Memoria
    # -------------------------------------------------------------------------

    def reset_memory(self) -> None:
        """
        Resetea la memoria conversacional.

        Limpia la sesión y genera un nuevo thread_id,
        empezando una conversación limpia. El agente se reinicializará
        en la próxima llamada a run().
        """
        if self._use_memory:
            self._memory_manager.clear_session(self._thread_id)
            self._checkpointer = self._memory_manager.get_checkpointer()
            self._thread_id = self._memory_manager.generate_thread_id()
            # Forzar reinicialización del agente con el nuevo checkpointer
            self._agent = None
            logger.info(f"Memory reset. New thread: {self._thread_id[:8]}...")
        else:
            logger.warning("reset_memory() llamado pero use_memory=False")

    def get_history(self) -> Optional[List]:
        """
        Devuelve el historial de mensajes del checkpointer para el thread actual.

        Returns:
            Lista de mensajes o None si no hay memoria habilitada.
        """
        return self._memory_manager.get_history(self._thread_id)

    @property
    def thread_id(self) -> str:
        """ID del thread actual de memoria."""
        return self._thread_id

    @thread_id.setter
    def thread_id(self, value: str) -> None:
        """
        Establece un thread_id específico (para reanudar conversaciones).

        Si el agente ya está inicializado, se reinicializará con el nuevo thread_id
        (el checkpointer mantiene el estado de todos los threads).
        """
        self._thread_id = value
        logger.info(f"Thread ID set to: {value[:8]}...")

    # -------------------------------------------------------------------------
    # Prompt
    # -------------------------------------------------------------------------

    def get_system_prompt(self, config: dict) -> str:
        """Genera el system prompt basado en la config del agente."""
        return get_system_prompt(config)

    # -------------------------------------------------------------------------
    # Run config builder
    # -------------------------------------------------------------------------

    def _build_run_config(self) -> dict:
        """
        Construye el config dict para `agent.ainvoke()`.

        Incluye callbacks y, si hay memoria, el thread_id estable.
        """
        run_config: dict = {"callbacks": self._callbacks}

        if self._use_memory:
            run_config["configurable"] = {"thread_id": self._thread_id}

        return run_config

    # -------------------------------------------------------------------------
    # Ejecución principal
    # -------------------------------------------------------------------------

    async def run(self, config: dict, max_retries: int = 3) -> dict:
        """
        Ejecuta el agente con retry automático ante errores de red.

        El agente se inicializa automáticamente si no lo está.
        Reutiliza la misma instancia del agente y checkpointer en todos
        los reintentos (mismo thread_id → acumula contexto).

        Args:
            config: Dict con product, provider, country_code, language, query.
                    Opcionalmente thread_id para reanudar una conversación.
            max_retries: Número máximo de reintentos ante errores de red.

        Returns:
            dict con status, output, y datos parseados.
        """
        # Auto-initialize si no se usó como context manager
        if self._agent is None:
            await self.initialize()

        # Permitir override del thread_id desde config
        if "thread_id" in config:
            self._thread_id = config["thread_id"]

        # Run config estable (mismo thread_id en todos los reintentos)
        run_config = self._build_run_config()

        last_error: Optional[str] = None
        failed_urls: List[str] = []

        for attempt in range(max_retries):
            # Construir mensajes frescos en cada intento
            system = self.get_system_prompt(config)
            human_msg = config.get("query", "Ejecuta la tarea según las instrucciones.")

            if failed_urls:
                human_msg += (
                    f"\n\nIMPORTANTE: Evita estas URLs que fallaron previamente: "
                    f"{', '.join(failed_urls[:5])}"
                )

            messages = [
                SystemMessage(content=system),
                HumanMessage(content=human_msg),
            ]

            try:
                result = await self._agent.ainvoke(
                    {"messages": messages},
                    config=run_config,
                )

                final_message = result["messages"][-1]
                output = final_message.content

                # Verificar si el output contiene un error de red recuperable
                if _is_recoverable_error(output):
                    last_error = output
                    url = _extract_failed_url(output)
                    if url:
                        failed_urls.append(url)

                    if attempt < max_retries - 1:
                        logger.warning(
                            f"⚠️ Error de red detectado (intento {attempt + 1}/{max_retries}), "
                            f"reintentando..."
                        )
                        # Resetear memoria para evitar estado corrupto
                        if self._use_memory:
                            self._memory_manager.clear_session(self._thread_id)
                            self._checkpointer = self._memory_manager.get_checkpointer()
                            self._thread_id = self._memory_manager.generate_thread_id()
                            self._agent = None
                            await self.initialize()
                            run_config = self._build_run_config()
                        continue

                # --- Structured output ---
                structured_response = await self._output_parser.extract_structured(
                    result=result,
                    output=output,
                    llm=self.llm,
                    config=config,
                )

                # Parsear output texto (skip si hay structured output)
                has_structured = structured_response is not None
                parsed = {} if has_structured else self._output_parser.parse_text(output)

                response = {
                    "status": "success",
                    "output": output,
                    "messages_count": len(result["messages"]),
                    "attempts": attempt + 1,
                    "thread_id": self._thread_id,
                    "has_structured_output": has_structured,
                    **parsed,
                }

                if has_structured:
                    response["structured_response"] = structured_response

                return response

            except Exception as e:
                last_error = str(e)
                url = _extract_failed_url(last_error)
                if url:
                    failed_urls.append(url)

                # "No web results found" = búsqueda sin resultados, no error de red
                # Devolver como resultado parcial en vez de reintentar
                if _is_no_data_error(last_error):
                    logger.warning(f"⚠️ Búsqueda sin resultados: {e}")
                    return {
                        "status": "partial",
                        "output": f"No se encontraron datos suficientes para la consulta. "
                                  f"La búsqueda web no devolvió resultados relevantes.",
                        "attempts": attempt + 1,
                        "thread_id": self._thread_id,
                    }

                if _is_recoverable_error(last_error) and attempt < max_retries - 1:
                    logger.warning(f"⚠️ Error de red (intento {attempt + 1}/{max_retries}): {e}")
                    # Resetear memoria para evitar estado corrupto (tool_use sin tool_result)
                    if self._use_memory:
                        self._memory_manager.clear_session(self._thread_id)
                        self._checkpointer = self._memory_manager.get_checkpointer()
                        self._thread_id = self._memory_manager.generate_thread_id()
                        self._agent = None
                        await self.initialize()
                        run_config = self._build_run_config()
                    continue

                logger.error(f"❌ Agent error (no recuperable): {e}")
                return {
                    "status": "error",
                    "output": str(e),
                    "attempts": attempt + 1,
                    "thread_id": self._thread_id,
                }

        # Agotamos todos los reintentos
        logger.error(f"❌ Agent error: agotados {max_retries} reintentos")
        return {
            "status": "error",
            "output": f"Error después de {max_retries} intentos: {last_error}",
            "attempts": max_retries,
            "thread_id": self._thread_id,
        }

    # -------------------------------------------------------------------------
    # Output parsing (delegado a OutputParser)
    # -------------------------------------------------------------------------

    def parse_output(self, output: str) -> dict:
        """
        Parsea el output del LLM extrayendo queries, URLs y uso de Playwright.

        Delegado a OutputParser para reutilización y testabilidad.
        """
        return self._output_parser.parse_text(output)
