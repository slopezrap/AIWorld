"""
Test del ScraperAgent BASE para electricidad.

Usa el mismo agente base, solo cambia la config.
La query se construye desde query_template en config.json.
Los prompts específicos de extracción/validación vienen del config.json.
"""

import asyncio
import json
import logging
import sys
sys.path.insert(0, '.')

# Configurar logging para ver los logs del agente en tiempo real
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
)

from datetime import datetime
from aifoundry.app.core.agents.base.agent import ScraperAgent
from aifoundry.app.utils.country import get_country_info

# Meses en español
MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}

def get_date_spanish():
    """Fecha en formato español: '14 enero 2026'."""
    now = datetime.now()
    return f"{now.day} {MESES_ES[now.month]} {now.year}"


async def main():
    """Test de scraping de electricidad con ScraperAgent base."""
    
    # Cargar config desde JSON
    with open("aifoundry/app/core/agents/electricity/config.json") as f:
        config_file = json.load(f)
    
    # Endesa en España
    country = "ES"
    provider = "Endesa"
    
    # Obtener datos del país
    country_info = get_country_info(country)
    country_name = country_info["name"]
    language = config_file["countries"][country]["language"]
    date = get_date_spanish()
    
    # Construir query desde template
    query_template = config_file.get("query_template", "precio {product} {provider} {country_name} {date}")
    query = query_template.format(
        provider=provider,
        country_name=country_name,
        date=date,
    )
    
    # Config para el agente - incluye prompts específicos del config.json
    agent_config = {
        "product": config_file["product"],
        "provider": provider,
        "country_code": country,
        "language": language,
        "query": query,
        "freshness": config_file.get("freshness", "pw"),
        # Prompts específicos de electricidad (vienen del config.json)
        "extraction_prompt": config_file.get("extraction_prompt", ""),
        "validation_prompt": config_file.get("validation_prompt", ""),
    }
    
    print("="*60)
    print("TEST: ScraperAgent para ELECTRICIDAD")
    print("="*60)
    print(f"Product: {agent_config['product']}")
    print(f"Provider: {agent_config['provider']}")
    print(f"Country: {agent_config['country_code']} ({country_name})")
    print(f"Query: {agent_config['query']}")
    print(f"Freshness: {agent_config['freshness']}")
    print(f"Extraction prompt: {'SI' if agent_config['extraction_prompt'] else 'NO'}")
    print(f"Validation prompt: {'SI' if agent_config['validation_prompt'] else 'NO'}")
    print("="*60)
    
    async with ScraperAgent(
        use_mcp=True, 
        disable_simple_scrape=True, 
        verbose=True,
    ) as agent:
        result = await agent.run(agent_config)
    
    print("\n" + "="*60)
    print("RESULTADO FINAL")
    print("="*60)
    print(f"Status: {result.get('status')}")
    print(f"URLs: {len(result.get('urls', []))}")
    print(f"Output length: {len(result.get('output', ''))} chars")
    
    if result.get('status') == 'success':
        print("\n" + "="*60)
        print("OUTPUT (primeros 2000 chars)")
        print("="*60)
        print(result.get('output', '')[:2000])
    
    return result


if __name__ == "__main__":
    asyncio.run(main())