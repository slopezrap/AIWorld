"""
Tests unitarios para utils/parsing.py — parse_agent_output().

Cubre los diferentes formatos de output que puede generar el LLM:
- Query en español (QUERY_ESPAÑOL)
- Query final (QUERY_FINAL)
- Fallback query_es → query_final
- Extracción de URLs
- Detección de Playwright
- Output vacío / sin matches
- Múltiples URLs (cap a 10)
"""

import pytest
from aifoundry.app.utils.parsing import parse_agent_output


# ─── QUERY EN ESPAÑOL ────────────────────────────────────────────────────────

class TestQueryEspanol:
    def test_query_espanol_format_standard(self):
        output = "QUERY_ESPAÑOL: precio electricidad España febrero 2026\nOtro texto"
        result = parse_agent_output(output)
        assert result["query_es"] == "precio electricidad España febrero 2026"

    def test_query_espanol_format_with_quotes(self):
        output = 'query en español: "salario ingeniero Madrid"\nfin'
        result = parse_agent_output(output)
        assert result["query_es"] == "salario ingeniero Madrid"

    def test_query_espanol_single_quotes(self):
        output = "query español: 'precio luz Iberdrola'\nfin"
        result = parse_agent_output(output)
        assert result["query_es"] == "precio luz Iberdrola"

    def test_query_espanol_not_present(self):
        output = "No hay query aquí, solo texto normal."
        result = parse_agent_output(output)
        assert "query_es" not in result


# ─── QUERY FINAL ─────────────────────────────────────────────────────────────

class TestQueryFinal:
    def test_query_final_standard(self):
        output = "QUERY_FINAL: electricity price Spain 2026\nDone"
        result = parse_agent_output(output)
        assert result["query_final"] == "electricity price Spain 2026"

    def test_query_final_with_quotes(self):
        output = 'query final: "best salary data engineer"\nend'
        result = parse_agent_output(output)
        assert result["query_final"] == "best salary data engineer"

    def test_query_final_not_present(self):
        output = "Solo texto sin queries."
        result = parse_agent_output(output)
        assert "query_final" not in result


# ─── FALLBACK: query_es → query_final ────────────────────────────────────────

class TestQueryFallback:
    def test_fallback_query_es_to_final(self):
        """Si hay query_es pero no query_final, query_final = query_es."""
        output = "QUERY_ESPAÑOL: precio kWh España\nResultados aquí."
        result = parse_agent_output(output)
        assert result["query_es"] == "precio kWh España"
        assert result["query_final"] == "precio kWh España"

    def test_both_queries_present(self):
        """Si ambas están, cada una tiene su valor propio."""
        output = (
            "QUERY_ESPAÑOL: precio luz España\n"
            "QUERY_FINAL: electricity price Spain\n"
        )
        result = parse_agent_output(output)
        assert result["query_es"] == "precio luz España"
        assert result["query_final"] == "electricity price Spain"


# ─── EXTRACCIÓN DE URLs ──────────────────────────────────────────────────────

class TestUrls:
    def test_single_url(self):
        output = "Encontré datos en https://www.example.com/prices y más."
        result = parse_agent_output(output)
        assert "urls" in result
        assert "https://www.example.com/prices" in result["urls"]

    def test_multiple_urls(self):
        output = (
            "Fuentes:\n"
            "https://www.source1.com/data\n"
            "https://www.source2.org/report\n"
            "http://api.source3.net/v1/prices\n"
        )
        result = parse_agent_output(output)
        assert len(result["urls"]) == 3

    def test_url_dedup(self):
        """URLs duplicadas se eliminan."""
        output = (
            "Ver https://example.com/page y también https://example.com/page otra vez."
        )
        result = parse_agent_output(output)
        assert len(result["urls"]) == 1

    def test_url_max_10(self):
        """Máximo 10 URLs."""
        urls = "\n".join(f"https://site{i}.com/page" for i in range(15))
        output = f"URLs:\n{urls}\n"
        result = parse_agent_output(output)
        assert len(result["urls"]) == 10

    def test_url_trailing_punctuation_stripped(self):
        """Puntuación al final se limpia."""
        output = "Ver https://example.com/data, y https://other.com/info."
        result = parse_agent_output(output)
        assert "https://example.com/data" in result["urls"]
        assert "https://other.com/info" in result["urls"]

    def test_short_urls_ignored(self):
        """URLs muy cortas (<=10 chars) se ignoran."""
        output = "http://x.co fin"  # len("http://x.co") = 11, debería pasar
        result = parse_agent_output(output)
        assert "urls" in result

    def test_no_urls(self):
        output = "No hay enlaces aquí."
        result = parse_agent_output(output)
        assert "urls" not in result


# ─── DETECCIÓN DE PLAYWRIGHT ─────────────────────────────────────────────────

class TestPlaywright:
    def test_browser_navigate_detected(self):
        output = (
            "Usé browser_navigate para ir a https://example.com/page "
            "y extraje los datos."
        )
        result = parse_agent_output(output)
        assert result.get("used_playwright") is True
        assert "urls_playwright_success" in result

    def test_browser_snapshot_detected(self):
        output = "Hice browser_snapshot de la página."
        result = parse_agent_output(output)
        assert result.get("used_playwright") is True

    def test_playwright_keyword_detected(self):
        output = "Utilicé playwright para renderizar la página."
        result = parse_agent_output(output)
        assert result.get("used_playwright") is True

    def test_no_playwright(self):
        output = "Solo usé scraping simple con httpx."
        result = parse_agent_output(output)
        assert "used_playwright" not in result


# ─── EDGE CASES ──────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_string(self):
        result = parse_agent_output("")
        assert result == {}

    def test_none_like_output(self):
        """Output sin ningún patrón reconocible."""
        result = parse_agent_output("hola mundo, esto es un test básico.")
        assert result == {}

    def test_combined_output(self):
        """Output realista con queries, URLs y Playwright."""
        output = (
            "QUERY_ESPAÑOL: precio kWh Iberdrola Madrid 2026\n"
            "QUERY_FINAL: electricity price Iberdrola Madrid 2026\n\n"
            "Busqué en:\n"
            "https://www.iberdrola.es/tarifas\n"
            "https://www.ree.es/datos\n\n"
            "Usé browser_navigate para acceder a la web de Iberdrola.\n"
            "Los precios encontrados son 0.15€/kWh."
        )
        result = parse_agent_output(output)

        assert result["query_es"] == "precio kWh Iberdrola Madrid 2026"
        assert result["query_final"] == "electricity price Iberdrola Madrid 2026"
        assert len(result["urls"]) == 2
        assert result["used_playwright"] is True
        assert len(result["urls_playwright_success"]) == 2