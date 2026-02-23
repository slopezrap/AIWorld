"""
AIFoundry Agents.

Contiene los agentes con herramientas (tools).

ESTRUCTURA:
- base/: ScraperAgent con patrón ReAct (agente genérico)
- salary/: config.json para agente de salarios
- electricity/: config.json para agente de electricidad
- social_comments/: config.json para agente de comentarios en redes sociales
  
Cada agente solo necesita un config.json.
El ScraperAgent base se usa directamente con la config de cada dominio.
"""

from aifoundry.app.core.agents.base import (
    ScraperAgent,
    get_local_tools,
    simple_scrape_url,
    get_system_prompt,
)

__all__ = [
    "ScraperAgent",
    "get_local_tools",
    "simple_scrape_url",
    "get_system_prompt",
]
