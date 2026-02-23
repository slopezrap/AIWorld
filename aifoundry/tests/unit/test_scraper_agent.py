"""
Tests unitarios del ScraperAgent con LLM mockeado.

Red de seguridad ANTES de refactorizar agent.py.
Verifican la interfaz pública y el comportamiento del agente
sin llamadas reales a LLM ni a servicios MCP.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from aifoundry.app.core.agents.scraper.agent import (
    ScraperAgent,
    _is_recoverable_error,
    _is_no_data_error,
    _extract_failed_url,
    _tool_error_handler,
)


# ─── Test Response Models ────────────────────────────────────────────


class FakeStructuredResponse(BaseModel):
    """Modelo Pydantic fake para tests de structured output."""

    provider: str = Field(description="Provider name")
    country: str = Field(description="Country")
    summary: str = Field(description="Summary")


# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def basic_config():
    """Config mínima para ejecutar el agente."""
    return {
        "product": "test_product",
        "provider": "TestProvider",
        "country_code": "ES",
        "language": "es",
        "query": "buscar test product TestProvider España",
        "freshness": "pw",
    }


@pytest.fixture
def mock_llm():
    """Mock del LLM que devuelve get_llm()."""
    llm = MagicMock()
    llm.with_structured_output = MagicMock()
    return llm


@pytest.fixture
def mock_agent_response():
    """Respuesta estándar del agent executor (ainvoke)."""
    ai_msg = AIMessage(content="Resultado de búsqueda para test product. URL: https://example.com/data")
    return {
        "messages": [
            SystemMessage(content="System prompt"),
            HumanMessage(content="query"),
            ai_msg,
        ],
    }


@pytest.fixture
def mock_agent_response_with_structured():
    """Respuesta del agent executor con structured_response (native mode)."""
    ai_msg = AIMessage(content="Datos estructurados encontrados")
    fake_structured = FakeStructuredResponse(
        provider="TestProvider",
        country="España",
        summary="Resumen de test",
    )
    return {
        "messages": [
            SystemMessage(content="System prompt"),
            HumanMessage(content="query"),
            ai_msg,
        ],
        "structured_response": fake_structured,
    }


def _make_mock_agent_executor(response: dict) -> MagicMock:
    """Crea un mock del agent executor que devuelve la respuesta dada."""
    executor = MagicMock()
    executor.ainvoke = AsyncMock(return_value=response)
    return executor


# ─── Patches comunes ─────────────────────────────────────────────────


def _get_common_patches(mock_llm_instance=None):
    """Retorna dict de patches comunes para todos los tests."""
    llm = mock_llm_instance or MagicMock()
    return {
        "aifoundry.app.core.agents.scraper.agent.get_llm": MagicMock(return_value=llm),
        "aifoundry.app.core.agents.scraper.agent.get_mcp_configs": MagicMock(
            return_value={
                "brave": {"transport": "streamable_http", "url": "http://fake:8082/mcp"},
                "playwright": {"transport": "streamable_http", "url": "http://fake:8931/mcp"},
            }
        ),
    }


# ─── Tests: Error helpers (funciones puras) ──────────────────────────


class TestErrorHelpers:
    """Tests de funciones helper de detección de errores."""

    def test_is_recoverable_error_timeout(self):
        assert _is_recoverable_error("Connection timeout after 30s") is True

    def test_is_recoverable_error_connection_refused(self):
        assert _is_recoverable_error("Connection refused on port 8080") is True

    def test_is_recoverable_error_http2(self):
        assert _is_recoverable_error("ERR_HTTP2_PROTOCOL_ERROR") is True

    def test_is_recoverable_error_ssl(self):
        assert _is_recoverable_error("SSL_ERROR_HANDSHAKE_FAILURE") is True

    def test_is_recoverable_error_false(self):
        assert _is_recoverable_error("Invalid JSON format") is False

    def test_is_recoverable_error_empty(self):
        assert _is_recoverable_error("") is False

    def test_is_no_data_error_true(self):
        assert _is_no_data_error("No web results found for query") is True

    def test_is_no_data_error_false(self):
        assert _is_no_data_error("Connection timeout") is False

    def test_extract_failed_url(self):
        url = _extract_failed_url("Error accessing https://example.com/page in browser")
        assert url == "https://example.com/page"

    def test_extract_failed_url_none(self):
        assert _extract_failed_url("No URL here") is None

    def test_tool_error_handler_no_data(self):
        result = _tool_error_handler(Exception("No web results found"))
        assert "No se encontraron resultados" in result

    def test_tool_error_handler_generic(self):
        result = _tool_error_handler(Exception("Something went wrong"))
        assert "Error en herramienta" in result


# ─── Tests: ScraperAgent Initialization ──────────────────────────────


class TestScraperAgentInit:
    """Tests de inicialización del ScraperAgent."""

    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    def test_constructor_defaults(self, mock_get_llm):
        """El constructor crea el agente con valores por defecto."""
        mock_get_llm.return_value = MagicMock()
        agent = ScraperAgent()

        assert agent._use_mcp is True
        assert agent._verbose is True
        assert agent._use_memory is True
        assert agent._structured_output is False
        assert agent._response_model is None
        assert agent._agent is None
        assert agent._all_tools is None
        assert agent._checkpointer is not None

    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    def test_constructor_with_response_model(self, mock_get_llm):
        """Constructor con response_model activa structured output nativo."""
        mock_get_llm.return_value = MagicMock()
        agent = ScraperAgent(response_model=FakeStructuredResponse)

        assert agent._response_model is FakeStructuredResponse
        assert agent._structured_output is False  # No legacy

    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    def test_constructor_structured_output_deprecation(self, mock_get_llm):
        """structured_output=True sin response_model emite DeprecationWarning."""
        mock_get_llm.return_value = MagicMock()
        with pytest.warns(DeprecationWarning, match="structured_output=True está DEPRECATED"):
            ScraperAgent(structured_output=True)

    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    def test_constructor_disable_simple_scrape(self, mock_get_llm):
        """disable_simple_scrape filtra la tool simple_scrape_url."""
        mock_get_llm.return_value = MagicMock()
        agent = ScraperAgent(disable_simple_scrape=True)

        # Verificar que el ToolResolver fue configurado con disable_simple_scrape
        local_tools = agent._tool_resolver._get_local_tools()
        tool_names = [t.name for t in local_tools]
        assert "simple_scrape_url" not in tool_names

    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    def test_constructor_no_memory(self, mock_get_llm):
        """use_memory=False no crea checkpointer."""
        mock_get_llm.return_value = MagicMock()
        agent = ScraperAgent(use_memory=False)

        assert agent._checkpointer is None


# ─── Tests: ScraperAgent Context Manager & Initialize ────────────────


class TestScraperAgentLifecycle:
    """Tests del ciclo de vida: initialize, aenter, aexit."""

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.tool_executor.MultiServerMCPClient")
    @patch("aifoundry.app.core.agents.scraper.tool_executor.get_mcp_configs")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_aenter_initializes_agent(
        self, mock_get_llm, mock_get_mcp_configs, mock_mcp_client_cls, mock_create_agent
    ):
        """__aenter__ inicializa MCP tools, local tools y crea el agent executor."""
        mock_get_llm.return_value = MagicMock()

        # Mock MCP configs
        mock_get_mcp_configs.return_value = {
            "brave": {"transport": "streamable_http", "url": "http://fake:8082/mcp"},
        }

        # Mock MCP client
        mock_mcp_instance = MagicMock()
        mock_mcp_tool = MagicMock()
        mock_mcp_tool.name = "brave_web_search"
        mock_mcp_instance.get_tools = AsyncMock(return_value=[mock_mcp_tool])
        mock_mcp_client_cls.return_value = mock_mcp_instance

        # Mock create_agent
        mock_executor = MagicMock()
        mock_create_agent.return_value = mock_executor

        async with ScraperAgent(use_mcp=True, verbose=False) as agent:
            # Verificar que se inicializó
            assert agent._agent is not None
            assert agent._all_tools is not None
            assert len(agent._all_tools) > 0

            # Verificar que create_agent fue llamado
            mock_create_agent.assert_called_once()
            call_kwargs = mock_create_agent.call_args
            assert "model" in call_kwargs.kwargs or len(call_kwargs.args) > 0

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.tool_executor.get_mcp_configs")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_aenter_without_mcp(
        self, mock_get_llm, mock_get_mcp_configs, mock_create_agent
    ):
        """Sin MCP, solo carga tools locales."""
        mock_get_llm.return_value = MagicMock()
        mock_create_agent.return_value = MagicMock()

        async with ScraperAgent(use_mcp=False, verbose=False) as agent:
            assert agent._agent is not None
            # Solo tools locales
            tool_names = [t.name for t in agent._all_tools]
            assert "simple_scrape_url" in tool_names
            # No debería haber llamado a get_mcp_configs
            mock_get_mcp_configs.assert_not_called()

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.tool_executor.MultiServerMCPClient")
    @patch("aifoundry.app.core.agents.scraper.tool_executor.get_mcp_configs")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_aenter_mcp_failure_graceful(
        self, mock_get_llm, mock_get_mcp_configs, mock_mcp_client_cls, mock_create_agent
    ):
        """Si MCP falla al inicializar, continúa solo con tools locales."""
        mock_get_llm.return_value = MagicMock()
        mock_get_mcp_configs.return_value = {"brave": {"url": "http://fake"}}
        mock_mcp_client_cls.side_effect = Exception("MCP connection failed")
        mock_create_agent.return_value = MagicMock()

        async with ScraperAgent(use_mcp=True, verbose=False) as agent:
            assert agent._agent is not None
            # Solo tools locales (MCP falló)
            tool_names = [t.name for t in agent._all_tools]
            assert "simple_scrape_url" in tool_names

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_cleanup_resets_state(self, mock_get_llm, mock_create_agent):
        """cleanup() limpia agent, tools y MCP client."""
        mock_get_llm.return_value = MagicMock()
        mock_create_agent.return_value = MagicMock()

        agent = ScraperAgent(use_mcp=False, verbose=False)
        await agent.initialize()
        assert agent._agent is not None

        await agent.cleanup()
        assert agent._agent is None
        assert agent._all_tools is None


# ─── Tests: ScraperAgent.run() ───────────────────────────────────────


class TestScraperAgentRun:
    """Tests de la ejecución principal del agente."""

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_run_basic_success(
        self, mock_get_llm, mock_create_agent, basic_config, mock_agent_response
    ):
        """run() con respuesta normal retorna status=success y output."""
        mock_get_llm.return_value = MagicMock()
        mock_executor = _make_mock_agent_executor(mock_agent_response)
        mock_create_agent.return_value = mock_executor

        async with ScraperAgent(use_mcp=False, verbose=False) as agent:
            result = await agent.run(basic_config)

        assert result["status"] == "success"
        assert "Resultado de búsqueda" in result["output"]
        assert result["attempts"] == 1
        assert "thread_id" in result

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_run_parses_urls(
        self, mock_get_llm, mock_create_agent, basic_config, mock_agent_response
    ):
        """run() parsea URLs del output."""
        mock_get_llm.return_value = MagicMock()
        mock_executor = _make_mock_agent_executor(mock_agent_response)
        mock_create_agent.return_value = mock_executor

        async with ScraperAgent(use_mcp=False, verbose=False) as agent:
            result = await agent.run(basic_config)

        # El mock_agent_response tiene "https://example.com/data"
        assert "urls" in result
        assert "https://example.com/data" in result["urls"]

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_run_with_native_structured_output(
        self,
        mock_get_llm,
        mock_create_agent,
        basic_config,
        mock_agent_response_with_structured,
    ):
        """run() con response_model extrae structured_response del resultado."""
        mock_get_llm.return_value = MagicMock()
        mock_executor = _make_mock_agent_executor(mock_agent_response_with_structured)
        mock_create_agent.return_value = mock_executor

        async with ScraperAgent(
            use_mcp=False, verbose=False, response_model=FakeStructuredResponse
        ) as agent:
            result = await agent.run(basic_config)

        assert result["status"] == "success"
        assert result["has_structured_output"] is True
        assert result["structured_response"] is not None
        assert isinstance(result["structured_response"], FakeStructuredResponse)
        assert result["structured_response"].provider == "TestProvider"

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_run_native_structured_fallback_to_legacy(
        self, mock_get_llm, mock_create_agent, basic_config, mock_agent_response
    ):
        """Si native structured output no está en el resultado, hace fallback a post-processing."""
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        # El mock_agent_response NO tiene "structured_response" → fallback
        mock_executor = _make_mock_agent_executor(mock_agent_response)
        mock_create_agent.return_value = mock_executor

        # Mock del fallback with_structured_output
        fake_result = FakeStructuredResponse(
            provider="TestProvider", country="España", summary="Fallback"
        )
        mock_structured_llm = MagicMock()
        mock_structured_llm.ainvoke = AsyncMock(return_value=fake_result)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured_llm)

        async with ScraperAgent(
            use_mcp=False, verbose=False, response_model=FakeStructuredResponse
        ) as agent:
            result = await agent.run(basic_config)

        assert result["status"] == "success"
        assert result["has_structured_output"] is True
        assert result["structured_response"].summary == "Fallback"
        # Verificar que se usó with_structured_output como fallback
        mock_llm.with_structured_output.assert_called_once_with(FakeStructuredResponse)

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_run_legacy_structured_output(
        self, mock_get_llm, mock_create_agent, basic_config, mock_agent_response
    ):
        """structured_output=True sin response_model usa post-processing (legacy)."""
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_executor = _make_mock_agent_executor(mock_agent_response)
        mock_create_agent.return_value = mock_executor

        # Mock with_structured_output para legacy mode
        fake_result = MagicMock()
        mock_structured_llm = MagicMock()
        mock_structured_llm.ainvoke = AsyncMock(return_value=fake_result)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured_llm)

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            async with ScraperAgent(
                use_mcp=False, verbose=False, structured_output=True
            ) as agent:
                # Config necesita "product" para legacy structured
                result = await agent.run(basic_config)

        assert result["status"] == "success"
        assert result["has_structured_output"] is True

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_run_without_structured_output(
        self, mock_get_llm, mock_create_agent, basic_config, mock_agent_response
    ):
        """run() sin structured output parsea output como texto libre."""
        mock_get_llm.return_value = MagicMock()
        mock_executor = _make_mock_agent_executor(mock_agent_response)
        mock_create_agent.return_value = mock_executor

        async with ScraperAgent(use_mcp=False, verbose=False) as agent:
            result = await agent.run(basic_config)

        assert result["status"] == "success"
        assert result["has_structured_output"] is False
        assert "structured_response" not in result


# ─── Tests: Retry & Error Handling ───────────────────────────────────


class TestScraperAgentRetry:
    """Tests de retry y manejo de errores."""

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_retry_on_recoverable_error(
        self, mock_get_llm, mock_create_agent, basic_config
    ):
        """Reintenta cuando el output contiene un error de red recuperable."""
        mock_get_llm.return_value = MagicMock()

        # Primera llamada: error recuperable en output
        error_response = {
            "messages": [
                AIMessage(content="Error: connection timeout accessing https://example.com"),
            ],
        }
        # Segunda llamada: éxito
        success_response = {
            "messages": [
                AIMessage(content="Datos encontrados correctamente"),
            ],
        }

        mock_executor = MagicMock()
        mock_executor.ainvoke = AsyncMock(side_effect=[error_response, success_response])
        mock_create_agent.return_value = mock_executor

        async with ScraperAgent(use_mcp=False, verbose=False) as agent:
            result = await agent.run(basic_config, max_retries=3)

        assert result["status"] == "success"
        assert result["attempts"] == 2

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_retry_on_exception_recoverable(
        self, mock_get_llm, mock_create_agent, basic_config
    ):
        """Reintenta cuando ainvoke lanza excepción recuperable."""
        mock_get_llm.return_value = MagicMock()

        # Primera llamada: excepción recuperable
        # Segunda llamada: éxito
        success_response = {
            "messages": [AIMessage(content="OK")],
        }
        mock_executor = MagicMock()
        mock_executor.ainvoke = AsyncMock(
            side_effect=[
                Exception("Connection timeout"),
                success_response,
            ]
        )
        mock_create_agent.return_value = mock_executor

        async with ScraperAgent(use_mcp=False, verbose=False) as agent:
            result = await agent.run(basic_config, max_retries=3)

        assert result["status"] == "success"
        assert result["attempts"] == 2

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_non_recoverable_exception_returns_error(
        self, mock_get_llm, mock_create_agent, basic_config
    ):
        """Excepción no recuperable retorna status=error sin reintentar."""
        mock_get_llm.return_value = MagicMock()

        mock_executor = MagicMock()
        mock_executor.ainvoke = AsyncMock(
            side_effect=Exception("Invalid JSON format in response")
        )
        mock_create_agent.return_value = mock_executor

        async with ScraperAgent(use_mcp=False, verbose=False) as agent:
            result = await agent.run(basic_config, max_retries=3)

        assert result["status"] == "error"
        assert result["attempts"] == 1  # No reintentó

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_all_retries_exhausted_output_error(
        self, mock_get_llm, mock_create_agent, basic_config
    ):
        """Agota reintentos con error recuperable en output → devuelve success con output de error.

        Cuando el error está en el output (no excepción), el último intento
        se devuelve como success con el texto del error en output.
        """
        mock_get_llm.return_value = MagicMock()

        error_response = {
            "messages": [
                AIMessage(content="Error: timeout accessing page"),
            ],
        }
        mock_executor = MagicMock()
        mock_executor.ainvoke = AsyncMock(return_value=error_response)
        mock_create_agent.return_value = mock_executor

        async with ScraperAgent(use_mcp=False, verbose=False) as agent:
            result = await agent.run(basic_config, max_retries=2)

        # El agente devuelve el output tal cual en el último intento
        assert result["status"] == "success"
        assert "timeout" in result["output"]
        assert result["attempts"] == 2

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_all_retries_exhausted_exception(
        self, mock_get_llm, mock_create_agent, basic_config
    ):
        """Agota reintentos con excepciones recuperables → retorna error."""
        mock_get_llm.return_value = MagicMock()

        mock_executor = MagicMock()
        mock_executor.ainvoke = AsyncMock(
            side_effect=Exception("Connection timeout")
        )
        mock_create_agent.return_value = mock_executor

        async with ScraperAgent(use_mcp=False, verbose=False) as agent:
            result = await agent.run(basic_config, max_retries=2)

        assert result["status"] == "error"
        assert result["attempts"] == 2

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_no_data_error_returns_partial(
        self, mock_get_llm, mock_create_agent, basic_config
    ):
        """Error 'no web results' retorna status=partial sin reintentar."""
        mock_get_llm.return_value = MagicMock()

        mock_executor = MagicMock()
        mock_executor.ainvoke = AsyncMock(
            side_effect=Exception("No web results found for this query")
        )
        mock_create_agent.return_value = mock_executor

        async with ScraperAgent(use_mcp=False, verbose=False) as agent:
            result = await agent.run(basic_config, max_retries=3)

        assert result["status"] == "partial"
        assert "No se encontraron datos" in result["output"]
        assert result["attempts"] == 1  # No reintentó


# ─── Tests: Memory / Conversational ─────────────────────────────────


class TestScraperAgentMemory:
    """Tests de memoria conversacional."""

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_memory_same_thread_id(
        self, mock_get_llm, mock_create_agent, basic_config
    ):
        """Dos ejecuciones con el mismo agente comparten thread_id (memoria)."""
        mock_get_llm.return_value = MagicMock()

        response1 = {"messages": [AIMessage(content="Respuesta turno 1")]}
        response2 = {"messages": [AIMessage(content="Respuesta turno 2")]}

        mock_executor = MagicMock()
        mock_executor.ainvoke = AsyncMock(side_effect=[response1, response2])
        mock_create_agent.return_value = mock_executor

        async with ScraperAgent(use_mcp=False, verbose=False, use_memory=True) as agent:
            thread_id = agent.thread_id

            r1 = await agent.run(basic_config)
            r2 = await agent.run(basic_config)

        assert r1["status"] == "success"
        assert r2["status"] == "success"
        # Ambos usan el mismo thread_id
        assert r1["thread_id"] == thread_id
        assert r2["thread_id"] == thread_id

        # El executor fue llamado 2 veces con el mismo configurable.thread_id
        calls = mock_executor.ainvoke.call_args_list
        assert len(calls) == 2
        for call in calls:
            config_arg = call.kwargs.get("config") or call.args[1]
            assert config_arg["configurable"]["thread_id"] == thread_id

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_custom_thread_id_from_config(
        self, mock_get_llm, mock_create_agent, basic_config
    ):
        """thread_id en config override el thread_id del agente."""
        mock_get_llm.return_value = MagicMock()

        response = {"messages": [AIMessage(content="OK")]}
        mock_executor = _make_mock_agent_executor(response)
        mock_create_agent.return_value = mock_executor

        custom_config = {**basic_config, "thread_id": "my-custom-thread"}

        async with ScraperAgent(use_mcp=False, verbose=False) as agent:
            result = await agent.run(custom_config)

        assert result["thread_id"] == "my-custom-thread"

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_reset_memory(self, mock_get_llm, mock_create_agent):
        """reset_memory() genera nuevo thread_id y nuevo checkpointer."""
        mock_get_llm.return_value = MagicMock()
        mock_create_agent.return_value = MagicMock()

        agent = ScraperAgent(use_mcp=False, verbose=False, use_memory=True)
        await agent.initialize()

        old_thread = agent.thread_id
        old_checkpointer = agent._checkpointer

        agent.reset_memory()

        assert agent.thread_id != old_thread
        assert agent._checkpointer is not old_checkpointer
        # Agent se reinicializa en próximo run
        assert agent._agent is None

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_set_thread_id(self, mock_get_llm, mock_create_agent):
        """Se puede establecer un thread_id específico."""
        mock_get_llm.return_value = MagicMock()
        mock_create_agent.return_value = MagicMock()

        agent = ScraperAgent(use_mcp=False, verbose=False)
        await agent.initialize()

        agent.thread_id = "resume-session-123"
        assert agent.thread_id == "resume-session-123"

        await agent.cleanup()


# ─── Tests: System Prompt ────────────────────────────────────────────


class TestScraperAgentPrompt:
    """Tests de generación de system prompt."""

    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    def test_get_system_prompt(self, mock_get_llm, basic_config):
        """get_system_prompt() genera prompt válido desde config."""
        mock_get_llm.return_value = MagicMock()
        agent = ScraperAgent(use_mcp=False, verbose=False)

        prompt = agent.get_system_prompt(basic_config)
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        # Debería contener el product y provider
        assert "test_product" in prompt
        assert "TestProvider" in prompt

    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    def test_get_system_prompt_with_extraction(self, mock_get_llm, basic_config):
        """Prompt incluye extraction_prompt si está en config."""
        mock_get_llm.return_value = MagicMock()
        agent = ScraperAgent(use_mcp=False, verbose=False)

        config_with_extraction = {
            **basic_config,
            "extraction_prompt": "Extrae tarifas y precios por kWh",
        }
        prompt = agent.get_system_prompt(config_with_extraction)
        assert "Extrae tarifas y precios por kWh" in prompt


# ─── Tests: Output Parsing ───────────────────────────────────────────


class TestScraperAgentParsing:
    """Tests del parsing de output."""

    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    def test_parse_output_extracts_urls(self, mock_get_llm):
        """parse_output() extrae URLs del texto."""
        mock_get_llm.return_value = MagicMock()
        agent = ScraperAgent(use_mcp=False, verbose=False)

        output = "Encontré datos en https://glassdoor.com/salary y https://indeed.com/jobs"
        parsed = agent.parse_output(output)

        assert "urls" in parsed
        assert "https://glassdoor.com/salary" in parsed["urls"]
        assert "https://indeed.com/jobs" in parsed["urls"]

    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    def test_parse_output_detects_playwright(self, mock_get_llm):
        """parse_output() detecta uso de Playwright."""
        mock_get_llm.return_value = MagicMock()
        agent = ScraperAgent(use_mcp=False, verbose=False)

        output = "Usé browser_navigate para acceder a https://example.com"
        parsed = agent.parse_output(output)

        assert parsed.get("used_playwright") is True

    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    def test_parse_output_empty(self, mock_get_llm):
        """parse_output() con texto sin datos retorna dict vacío."""
        mock_get_llm.return_value = MagicMock()
        agent = ScraperAgent(use_mcp=False, verbose=False)

        parsed = agent.parse_output("Sin datos relevantes.")
        assert isinstance(parsed, dict)


# ─── Tests: Auto-initialize ─────────────────────────────────────────


class TestScraperAgentAutoInit:
    """Tests de auto-inicialización (sin context manager)."""

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_run_auto_initializes(
        self, mock_get_llm, mock_create_agent, basic_config
    ):
        """run() auto-inicializa si no se usó context manager."""
        mock_get_llm.return_value = MagicMock()

        response = {"messages": [AIMessage(content="Auto-init OK")]}
        mock_executor = _make_mock_agent_executor(response)
        mock_create_agent.return_value = mock_executor

        agent = ScraperAgent(use_mcp=False, verbose=False)
        assert agent._agent is None

        result = await agent.run(basic_config)
        assert result["status"] == "success"
        assert agent._agent is not None

        await agent.cleanup()

    @patch("aifoundry.app.core.agents.scraper.agent.create_agent")
    @patch("aifoundry.app.core.agents.scraper.agent.get_llm")
    async def test_initialize_is_idempotent(
        self, mock_get_llm, mock_create_agent
    ):
        """initialize() es idempotente — no recrea el agente si ya existe."""
        mock_get_llm.return_value = MagicMock()
        mock_create_agent.return_value = MagicMock()

        agent = ScraperAgent(use_mcp=False, verbose=False)
        await agent.initialize()
        first_agent = agent._agent

        await agent.initialize()
        assert agent._agent is first_agent  # Misma instancia
        # create_agent solo se llamó 1 vez
        assert mock_create_agent.call_count == 1

        await agent.cleanup()


# ─── Tests: Callback Handler ────────────────────────────────────────


class TestAgentCallbackHandler:
    """Tests del callback handler de logging."""

    def test_callback_handler_creation(self):
        """AgentCallbackHandler se crea correctamente."""
        from aifoundry.app.core.agents.scraper.agent import AgentCallbackHandler

        handler = AgentCallbackHandler(agent_name="test")
        assert handler.agent_name == "test"
        assert handler._first_llm is True
        assert handler._current_step is None

    def test_callback_tool_to_step_mapping(self):
        """El mapeo de tools a pasos está definido."""
        from aifoundry.app.core.agents.scraper.agent import AgentCallbackHandler

        handler = AgentCallbackHandler()
        assert "brave_web_search" in handler._TOOL_TO_STEP
        assert "simple_scrape_url" in handler._TOOL_TO_STEP
        assert "browser_navigate" in handler._TOOL_TO_STEP
