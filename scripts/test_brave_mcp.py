"""
Test Brave Search MCP

Script para probar la conexión con el MCP de Brave Search.
Imprime las tools disponibles.

Uso:
    PYTHONPATH=. python scripts/test_brave_mcp.py
"""

import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

from aifoundry.app.mcp_servers.externals.brave_search.brave_search_mcp import get_mcp_config


async def main():
    """Test de conexión con Brave Search MCP."""
    
    brave_config = get_mcp_config()
    
    mcp_config = {
        "brave-search": brave_config
    }
    
    print(f"\n📡 Conectando con configuración: {brave_config}")
    
    client = MultiServerMCPClient(mcp_config)
    tools = await client.get_tools()
    
    print("\n=== Brave Search MCP Tools ===")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")
    print("==============================\n")


if __name__ == "__main__":
    asyncio.run(main())
