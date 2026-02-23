"""
Tools locales para el ScraperAgent.

Las tools de MCP (brave_search, playwright) se cargan en el AGENTE.
Aquí solo tools locales que wrappean utilidades.
"""

import asyncio
import logging

from langchain_core.tools import tool

from aifoundry.app.utils.simple_scraper import simple_scrape as _simple_scrape
from aifoundry.app.utils.text import truncate_text

logger = logging.getLogger(__name__)


@tool
async def simple_scrape_url(url: str) -> str:
    """
    Scrapea una URL y devuelve el contenido en markdown.

    Usa esta tool para obtener el contenido de una página web.
    Funciona con sitios estáticos. Devuelve markdown limpio.

    Si falla o la página necesita JavaScript, usa playwright_navigate.

    Args:
        url: URL completa a scrapear (ej: https://example.com/page)

    Returns:
        Contenido de la página en markdown con título y fuente.
        Si falla, devuelve JSON con error y tip.
    """
    logger.info(f"🔧 scrape_url: {url[:60]}...")

    # Ejecutar scrape síncrono en un thread para no bloquear el event loop
    result = await asyncio.to_thread(_simple_scrape, url, ["markdown"])

    if result["success"]:
        data = result["data"]
        title = data["metadata"].get("title", "Sin título")
        markdown = data.get("markdown", "")
        source = data["metadata"].get("sourceURL", url)

        # Truncar para no saturar contexto
        truncated = truncate_text(markdown, 10000)

        output = f"""# {title}

{truncated}

---
Source: {source}"""

        logger.info(f"   ✅ {len(markdown)} chars → {len(truncated)} chars")
        return output

    else:
        error = result.get("error", "Error desconocido")
        logger.warning(f"   ❌ {error}")
        return f'{{"error": "{error}", "url": "{url}", "tip": "Intenta con playwright_navigate"}}'


# Lista de tools locales
LOCAL_TOOLS = [simple_scrape_url]


def get_local_tools():
    """Devuelve las tools locales del scraper."""
    return LOCAL_TOOLS.copy()