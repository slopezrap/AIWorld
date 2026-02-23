"""
Brave Search MCP Server (External)

Configuración para el MCP de Brave Search que se ejecuta como servicio externo.
Solo proporciona la configuración de conexión - es un servicio Docker externo.
"""

from typing import Dict, Any
from aifoundry.app.config import settings


def get_mcp_config(headers: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Devuelve la configuración del MCP Brave Search para langchain-mcp-adapters

    Args:
        headers: Headers adicionales (opcional)

    Returns:
        Dict con la configuración del MCP
    """
    config = {
        "transport": "streamable_http",
        "url": settings.brave_search_mcp_url,
    }

    if headers:
        config["headers"] = headers

    return config
