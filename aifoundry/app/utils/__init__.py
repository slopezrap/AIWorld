"""
Utils - Utilidades compartidas por todos los agentes.

Basado en HEFESTO - Patrón simétrico.
"""

from .simple_scraper import simple_scrape
from .text import parse_json_response, extract_urls, truncate_text, clean_markdown_code_blocks
from .country import get_country_info, COUNTRY_INFO
from .rate_limiter import BraveRateLimiter, get_brave_rate_limiter

__all__ = [
    # Scraper
    "simple_scrape",
    # Text
    "parse_json_response",
    "extract_urls",
    "truncate_text",
    "clean_markdown_code_blocks",
    # Country
    "get_country_info",
    "COUNTRY_INFO",
    # Rate Limiter
    "BraveRateLimiter",
    "get_brave_rate_limiter",
]
