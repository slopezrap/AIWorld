"""
Test Playwright MCP

Script para probar la conexión con el MCP de Playwright.
Imprime las tools disponibles.

Uso:
    PYTHONPATH=. python scripts/test_playwright_mcp.py
"""

import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

from aifoundry.app.mcp_servers.externals.playwright.playwright_mcp import get_mcp_config


async def main():
    """Test de conexión con Playwright MCP."""
    
    playwright_config = get_mcp_config()
    
    mcp_config = {
        "playwright": playwright_config
    }
    
    print(f"\n📡 Conectando con configuración: {playwright_config}")
    
    client = MultiServerMCPClient(mcp_config)
    tools = await client.get_tools()
    
    print("\n=== Playwright MCP Tools ===")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:100]}...")
    print("============================\n")


if __name__ == "__main__":
    asyncio.run(main())
