"""
Base Scraper Agent.

Módulo base para agentes de scraping con patrón ReAct.
"""

from aifoundry.app.core.agents.scraper.agent import ScraperAgent
from aifoundry.app.core.agents.scraper.config_schema import AgentConfig, CountryConfig
from aifoundry.app.core.agents.scraper.tools import get_local_tools, simple_scrape_url
from aifoundry.app.core.agents.scraper.prompts import get_system_prompt

__all__ = [
    "ScraperAgent",
    "get_local_tools",
    "simple_scrape_url",
    "get_system_prompt",
]
