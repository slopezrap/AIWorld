"""
Playwright MCP Server (External)

Configuración para el MCP de Playwright que se ejecuta como servicio externo.
"""

from typing import Dict, Any
from aifoundry.app.config import settings

# Nota: No instanciamos FastMCP porque es un servicio externo en Docker.
# Solo proporcionamos la configuración de conexión.

def get_mcp_config(headers: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Devuelve la configuración del MCP Playwright para langchain-mcp-adapters

    Args:
        headers: Headers adicionales (opcional)

    Returns:
        Dict con la configuración del MCP
    """
    config = {
        "transport": "streamable_http",
        "url": settings.playwright_mcp_url,
    }

    # Si hay headers, agregarlos
    if headers:
        config["headers"] = headers

    return config
