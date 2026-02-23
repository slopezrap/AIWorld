"""
Test del ScraperAgent BASE para salarios con Structured Output.

Usa el mismo agente base, solo cambia la config.
La query se construye desde query_template en config.json.
Structured output convierte el texto libre a objetos Pydantic validados.
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
from aifoundry.app.core.agents.scraper.agent import ScraperAgent
from aifoundry.app.schemas.agent_responses import SalaryResponse
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
    """Test de scraping de salarios con ScraperAgent base y Structured Output."""
    
    # Cargar config desde JSON
    with open("aifoundry/app/core/agents/scraper/salary/config.json") as f:
        config_file = json.load(f)
    
    # BCG Lead Enterprise Architect en Madrid, España
    country = "ES"
    provider = "BCG Boston Consulting Group"
    position = "Lead Enterprise Architect"
    city = "Madrid"
    
    # Obtener datos del país
    country_info = get_country_info(country)
    country_name = country_info["name"]
    language = config_file["countries"][country]["language"]
    
    # Query personalizada para BCG Lead Enterprise Architect en Madrid, enero 2026
    query = f"salario {position} {provider} {city} {country_name} enero 2026"
    
    # Config para el agente
    agent_config = {
        "product": config_file["product"],
        "provider": provider,
        "country_code": country,
        "language": language,
        "query": query,  # Query personalizada
        "freshness": config_file.get("freshness", "py")  # Último año
    }
    
    print("="*60)
    print("TEST: ScraperAgent para SALARIOS (con Structured Output)")
    print("="*60)
    print(f"Product: {agent_config['product']}")
    print(f"Provider: {agent_config['provider']}")
    print(f"Country: {agent_config['country_code']} ({country_name})")
    print(f"Query: {agent_config['query']}")
    print(f"Freshness: {agent_config['freshness']}")
    print(f"Structured Output: NATIVO via response_model (1 sola llamada LLM)")
    print("="*60)
    
    # response_model= habilita structured output NATIVO (1 sola pasada LLM)
    # Reemplaza al legacy structured_output=True (que hacía 2 llamadas LLM)
    async with ScraperAgent(
        use_mcp=True, 
        disable_simple_scrape=True, 
        verbose=True,
        response_model=SalaryResponse,  # <-- STRUCTURED OUTPUT NATIVO
    ) as agent:
        result = await agent.run(agent_config)
    
    print("\n" + "="*60)
    print("RESULTADO FINAL")
    print("="*60)
    print(f"Status: {result.get('status')}")
    print(f"Has Structured Output: {result.get('has_structured_output', False)}")
    print(f"Output length: {len(result.get('output', ''))} caracteres")
    
    # Mostrar structured output si existe
    if result.get('has_structured_output') and result.get('structured_response'):
        structured = result['structured_response']
        print("\n" + "="*60)
        print("📊 STRUCTURED OUTPUT (SalaryResponse)")
        print("="*60)
        
        # Mostrar campos del objeto Pydantic
        print(f"\n🏢 Provider: {structured.provider}")
        print(f"🌍 Country: {structured.country}")
        print(f"🔍 Query: {structured.query_used}")
        print(f"📅 Data Freshness: {structured.data_freshness}")
        print(f"🎯 Confidence: {structured.confidence}")
        
        print(f"\n💰 SALARIOS ENCONTRADOS ({len(structured.salaries)}):")
        for i, salary in enumerate(structured.salaries, 1):
            print(f"\n  [{i}] {salary.position}")
            if salary.salary_min:
                print(f"      💵 Mínimo: {salary.salary_min} {salary.currency}/{salary.salary_period}")
            if salary.salary_max:
                print(f"      💵 Máximo: {salary.salary_max} {salary.currency}/{salary.salary_period}")
            if salary.salary_avg:
                print(f"      💵 Promedio: {salary.salary_avg} {salary.currency}/{salary.salary_period}")
            if salary.source_url:
                print(f"      🔗 Fuente: {salary.source_url[:50]}...")
        
        print(f"\n📝 RESUMEN:")
        print(f"   {structured.summary[:500]}...")
        
        print(f"\n🔗 FUENTES ({len(structured.sources)}):")
        for url in structured.sources[:5]:
            print(f"   - {url}")
        
        if structured.notes:
            print(f"\n⚠️ NOTAS: {structured.notes}")
        
        # También mostrar como JSON para verificar
        print("\n" + "="*60)
        print("📄 STRUCTURED OUTPUT (JSON)")
        print("="*60)
        print(structured.model_dump_json(indent=2))
    else:
        print("\n⚠️ No hay salida estructurada, mostrando output raw:")
        print("="*60)
        print(result.get('output', '')[:2000])
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
