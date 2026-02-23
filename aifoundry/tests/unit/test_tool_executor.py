"""
Tests unitarios del módulo de resolución de tools.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aifoundry.app.core.agents.scraper.tool_executor import (
    ToolResolver,
    _tool_error_handler,
    _is_no_data_error,
)


class TestToolErrorHandler:
    """Tests del handler de errores de tools."""

    def test_no_data_returns_friendly_message(self):
        result = _tool_error_handler(Exception("No web results found"))
        assert "No se encontraron resultados" in result

    def test_generic_error_returns_error_message(self):
        result = _tool_error_handler(Exception("Connection refused"))
        assert "Error en herramienta" in result

    def test_long_error_truncated(self):
        long_msg = "x" * 1000
        result = _tool_error_handler(Exception(long_msg))
        assert len(result) < 600


class TestIsNoDataError:
    """Tests de detección de errores sin datos."""

    def test_no_web_results(self):
        assert _is_no_data_error("No web results found") is True

    def test_no_results_found(self):
        assert _is_no_data_error("No results found for query") is True

    def test_not_no_data(self):
        assert _is_no_data_error("Connection timeout") is False

    def test_empty_string(self):
        assert _is_no_data_error("") is False


class TestToolResolver:
    """Tests del ToolResolver."""

    def test_get_local_tools_default(self):
        """Sin MCP, obtiene tools locales."""
        resolver = ToolResolver(use_mcp=False)
        tools = resolver._get_local_tools()

        tool_names = [t.name for t in tools]
        assert "simple_scrape_url" in tool_names

    def test_get_local_tools_disable_scrape(self):
        """disable_simple_scrape excluye simple_scrape_url."""
        resolver = ToolResolver(use_mcp=False, disable_simple_scrape=True)
        tools = resolver._get_local_tools()

        tool_names = [t.name for t in tools]
        assert "simple_scrape_url" not in tool_names

    def test_get_local_tools_custom(self):
        """custom_tools sobreescribe las tools locales."""
        fake_tool = MagicMock()
        fake_tool.name = "custom_tool"
        resolver = ToolResolver(use_mcp=False, custom_tools=[fake_tool])
        tools = resolver._get_local_tools()

        assert len(tools) == 1
        assert tools[0].name == "custom_tool"

    @patch("aifoundry.app.core.agents.scraper.tool_executor.get_mcp_configs")
    @patch("aifoundry.app.core.agents.scraper.tool_executor.MultiServerMCPClient")
    async def test_resolve_tools_with_mcp(self, mock_mcp_cls, mock_get_configs):
        """resolve_tools() carga tools locales + MCP."""
        mock_get_configs.return_value = {
            "brave": {"url": "http://fake:8082/mcp"},
        }

        mock_mcp_tool = MagicMock()
        mock_mcp_tool.name = "brave_web_search"
        mock_mcp_instance = MagicMock()
        mock_mcp_instance.get_tools = AsyncMock(return_value=[mock_mcp_tool])
        mock_mcp_cls.return_value = mock_mcp_instance

        resolver = ToolResolver(use_mcp=True)
        tools = await resolver.resolve_tools()

        tool_names = [t.name for t in tools]
        assert "simple_scrape_url" in tool_names
        assert "brave_web_search" in tool_names

        # Verificar que se configuró error handler
        assert mock_mcp_tool.handle_tool_error is not None

        await resolver.cleanup()

    async def test_resolve_tools_without_mcp(self):
        """resolve_tools() sin MCP solo retorna tools locales."""
        resolver = ToolResolver(use_mcp=False)
        tools = await resolver.resolve_tools()

        tool_names = [t.name for t in tools]
        assert "simple_scrape_url" in tool_names
        assert resolver.mcp_client is None

    @patch("aifoundry.app.core.agents.scraper.tool_executor.get_mcp_configs")
    @patch("aifoundry.app.core.agents.scraper.tool_executor.MultiServerMCPClient")
    async def test_resolve_tools_mcp_failure_graceful(self, mock_mcp_cls, mock_get_configs):
        """Si MCP falla, retorna solo tools locales."""
        mock_get_configs.return_value = {"brave": {"url": "http://fake"}}
        mock_mcp_cls.side_effect = Exception("MCP connection failed")

        resolver = ToolResolver(use_mcp=True)
        tools = await resolver.resolve_tools()

        # Solo tools locales
        tool_names = [t.name for t in tools]
        assert "simple_scrape_url" in tool_names

    @patch("aifoundry.app.core.agents.scraper.tool_executor.get_mcp_configs")
    @patch("aifoundry.app.core.agents.scraper.tool_executor.MultiServerMCPClient")
    async def test_cleanup_closes_mcp(self, mock_mcp_cls, mock_get_configs):
        """cleanup() cierra el MCP client."""
        mock_get_configs.return_value = {"brave": {"url": "http://fake"}}

        mock_mcp_instance = MagicMock()
        mock_mcp_instance.get_tools = AsyncMock(return_value=[])
        mock_mcp_instance.close = AsyncMock()
        mock_mcp_cls.return_value = mock_mcp_instance

        resolver = ToolResolver(use_mcp=True)
        await resolver.resolve_tools()
        assert resolver.mcp_client is not None

        await resolver.cleanup()
        assert resolver.mcp_client is None
        mock_mcp_instance.close.assert_called_once()

    async def test_cleanup_no_mcp(self):
        """cleanup() sin MCP no lanza error."""
        resolver = ToolResolver(use_mcp=False)
        await resolver.cleanup()  # No debe lanzar