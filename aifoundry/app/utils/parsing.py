"""
Parsing utilities para output de agentes LLM.

Extraído de ScraperAgent.parse_output() para ser reutilizable
y testeable de forma independiente.
"""

import re
from typing import Dict, List


def parse_agent_output(output: str) -> Dict:
    """
    Parsea el output del LLM extrayendo queries, URLs y uso de Playwright.

    Args:
        output: Texto de respuesta del LLM.

    Returns:
        Dict con campos extraídos:
        - query_es: Query en español encontrada
        - query_final: Query final (o fallback de query_es)
        - urls: Lista de URLs encontradas (max 10)
        - used_playwright: True si se detectó uso de Playwright
        - urls_playwright_success: URLs extraídas si usó Playwright
    """
    result: Dict = {}
    output_lower = output.lower()

    # Buscar query en español
    for pattern in (
        r"QUERY_ESPAÑOL:\s*(.+?)(?:\n|$)",
        r'query.*español.*[:\s]+\"([^\"]+)\"',
        r"query.*español.*[:\s]+\'([^\']+)\'",
        r"query.*español.*[:\s]+(.+?)(?:\n|$)",
    ):
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            result["query_es"] = match.group(1).strip().strip("\"'")
            break

    # Buscar query final
    for pattern in (
        r"QUERY_FINAL:\s*(.+?)(?:\n|$)",
        r'query.*final.*[:\s]+\"([^\"]+)\"',
        r"query.*final.*[:\s]+\'([^\']+)\'",
        r"query.*final.*[:\s]+(.+?)(?:\n|$)",
    ):
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            result["query_final"] = match.group(1).strip().strip("\"'")
            break

    # Fallback: query_es → query_final
    if "query_es" in result and "query_final" not in result:
        result["query_final"] = result["query_es"]

    # Extraer URLs
    urls: List[str] = []
    for match in re.finditer(r"https?://[^\s\)\"'`\]<>]+", output):
        url = match.group().rstrip(".,;:")
        if url not in urls and len(url) > 10:
            urls.append(url)

    if urls:
        result["urls"] = urls[:10]

    # Detectar uso de Playwright
    playwright_indicators = ("browser_navigate", "browser_snapshot", "playwright")
    if any(ind in output_lower for ind in playwright_indicators):
        result["used_playwright"] = True
        result["urls_playwright_success"] = urls.copy()

    return result