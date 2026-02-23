"""
Módulo de resolución de tools para el ScraperAgent.

Encapsula la lógica de carga de tools locales y MCP,
incluyendo la configuración de error handlers.
"""

import logging
from typing import Optional, List, Dict

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from aifoundry.app.core.agents.scraper.tools import get_local_tools

logger = logging.getLogger(__name__)


# =============================================================================
# ERROR PATTERNS (usados por el tool error handler)
# =============================================================================

_NO_DATA_PATTERNS = (
    "no web results",
    "no results found",
)


def _is_no_data_error(text: str) -> bool:
    """Verifica si el error indica simplemente que no se encontraron datos."""
    if not text:
        return False
    text_lower = text.lower()
    return any(p in text_lower for p in _NO_DATA_PATTERNS)


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
# MCP CONFIG LOADER
# =============================================================================

def get_mcp_configs() -> Dict[str, Dict]:
    """Obtiene las configuraciones de los MCPs disponibles."""
    from aifoundry.app.mcp_servers.externals.brave_search.brave_search_mcp import (
        get_mcp_config as get_brave_config,
    )
    from aifoundry.app.mcp_servers.externals.playwright.playwright_mcp import (
        get_mcp_config as get_playwright_config,
    )

    return {
        "brave": get_brave_config(),
        "playwright": get_playwright_config(),
    }


# =============================================================================
# TOOL RESOLVER
# =============================================================================

class ToolResolver:
    """
    Resuelve y prepara las tools (locales + MCP) para el agente.

    Responsabilidades:
    - Cargar tools locales (simple_scrape_url, etc.)
    - Conectar a MCP servers y obtener tools remotas
    - Configurar error handlers en tools MCP
    - Limpiar conexiones MCP al finalizar
    """

    def __init__(
        self,
        use_mcp: bool = True,
        disable_simple_scrape: bool = False,
        custom_tools: Optional[List[BaseTool]] = None,
    ):
        """
        Args:
            use_mcp: Si cargar tools MCP (Brave, Playwright).
            disable_simple_scrape: Si True, excluye simple_scrape_url.
            custom_tools: Tools custom en vez de las por defecto.
        """
        self._use_mcp = use_mcp
        self._disable_simple_scrape = disable_simple_scrape
        self._custom_tools = custom_tools
        self._mcp_client: Optional[MultiServerMCPClient] = None

    def _get_local_tools(self) -> List[BaseTool]:
        """Obtiene las tools locales según la configuración."""
        if self._custom_tools is not None:
            return list(self._custom_tools)

        all_local = get_local_tools()
        if self._disable_simple_scrape:
            return [t for t in all_local if t.name != "simple_scrape_url"]
        return list(all_local)

    async def resolve_tools(self) -> List[BaseTool]:
        """
        Resuelve todas las tools disponibles (locales + MCP).

        Returns:
            Lista de todas las tools listas para usar.
        """
        all_tools = self._get_local_tools()

        if self._use_mcp:
            try:
                mcp_configs = get_mcp_configs()
                self._mcp_client = MultiServerMCPClient(mcp_configs)
                mcp_tools = await self._mcp_client.get_tools()

                # Configurar manejo de errores en tools MCP
                for t in mcp_tools:
                    t.handle_tool_error = _tool_error_handler

                all_tools.extend(mcp_tools)
                logger.info(f"MCP tools loaded: {[t.name for t in mcp_tools]}")
            except Exception as e:
                logger.warning(
                    f"Error cargando MCP tools: {e}. Continuando solo con tools locales."
                )

        return all_tools

    async def cleanup(self) -> None:
        """Libera recursos (cierra MCP client)."""
        if self._mcp_client:
            try:
                if hasattr(self._mcp_client, "close"):
                    await self._mcp_client.close()
            except Exception as e:
                logger.debug(f"Error cerrando MCP client: {e}")
            finally:
                self._mcp_client = None

    @property
    def mcp_client(self) -> Optional[MultiServerMCPClient]:
        """Acceso al MCP client (para inspección/testing)."""
        return self._mcp_client