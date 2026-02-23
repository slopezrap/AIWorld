"""
SimpleScraper - Web scraper minimalista inspirado en Firecrawl.

API simple y limpia para scraping web con conversión a Markdown.
Referencia: https://docs.firecrawl.dev/features/scrape

FEATURES:
- Sync first: Sin async para simplificar uso
- Multiple formats: markdown, html, rawHtml, links
- Clean output: Solo contenido principal (sin nav, ads, etc)
- Rich metadata: title, description, language, og:*
- Simple API: Una función, parámetros claros

DIFERENCIA CON scraper.py:
| scraper.py        | simple_scraper.py  |
|-------------------|-------------------|
| Async             | Sync              |
| Escalada auto     | Solo HTTP         |
| Muchos params     | Pocos params      |
| Para agentes      | Para uso directo  |

Example:
    >>> result = simple_scrape("https://example.com", formats=["markdown"])
    >>> if result["success"]:
    ...     print(result["data"]["markdown"])
"""

import logging
import random
import re
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from readability import Document

logger = logging.getLogger(__name__)

# User agents rotativos para evitar bloqueos
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# Formatos soportados
SUPPORTED_FORMATS = {"markdown", "html", "rawHtml", "links"}


def _get_headers() -> Dict[str, str]:
    """Genera headers para parecer un navegador real."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }


def _extract_metadata(soup: BeautifulSoup, url: str, status_code: int, title_override: str = "") -> Dict[str, Any]:
    """
    Extrae metadata de la página.
    
    Args:
        soup: BeautifulSoup parseado
        url: URL original
        status_code: Código de estado HTTP
        title_override: Título extraído por readability (opcional)
        
    Returns:
        Dict con metadata completa
    """
    metadata = {
        "title": title_override or (soup.title.string.strip() if soup.title and soup.title.string else ""),
        "description": "",
        "language": soup.html.get("lang", "") if soup.html else "",
        "keywords": "",
        "robots": "",
        "ogTitle": "",
        "ogDescription": "",
        "ogUrl": "",
        "ogImage": "",
        "ogSiteName": "",
        "ogType": "",
        "sourceURL": url,
        "statusCode": status_code,
    }

    # Meta tags estándar
    for name, key in [("description", "description"), ("keywords", "keywords"), ("robots", "robots")]:
        tag = soup.find("meta", attrs={"name": name})
        if tag:
            metadata[key] = tag.get("content", "")

    # Open Graph tags
    og_mappings = {
        "og:title": "ogTitle",
        "og:description": "ogDescription",
        "og:url": "ogUrl",
        "og:image": "ogImage",
        "og:site_name": "ogSiteName",
        "og:type": "ogType",
    }
    
    for og_prop, meta_key in og_mappings.items():
        tag = soup.find("meta", property=og_prop)
        if tag:
            metadata[meta_key] = tag.get("content", "")

    # Twitter Card como fallback
    if not metadata["ogImage"]:
        twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_image:
            metadata["ogImage"] = twitter_image.get("content", "")

    return metadata


def _extract_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    """
    Extrae todos los links de la página.
    
    Args:
        soup: BeautifulSoup parseado
        base_url: URL base para resolver links relativos
        
    Returns:
        Lista de URLs únicas
    """
    links: Set[str] = set()
    
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        
        # Ignorar anchors, javascript, mailto, tel
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
            
        # Resolver URLs relativas
        full_url = urljoin(base_url, href)
        
        # Solo incluir http/https
        parsed = urlparse(full_url)
        if parsed.scheme in ("http", "https"):
            # Limpiar fragmentos
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                clean_url += f"?{parsed.query}"
            links.add(clean_url)
    
    return sorted(links)


def _clean_control_chars(text: str) -> str:
    """
    Elimina caracteres de control y NULL bytes que causan errores en lxml/readability.
    
    Args:
        text: Texto a limpiar
        
    Returns:
        Texto sin caracteres de control
    """
    # Eliminar NULL bytes y caracteres de control (excepto \t, \n, \r)
    # Los caracteres de control son 0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F
    cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', text)
    return cleaned


def _clean_html_for_markdown(html_content: str, use_readability: bool = True) -> tuple[str, str]:
    """
    Limpia HTML para conversión a Markdown.
    
    Args:
        html_content: HTML crudo
        use_readability: Si usar readability para extraer contenido principal
        
    Returns:
        Tuple de (html_limpio, título_extraído)
    """
    title = ""
    
    # Limpiar caracteres de control ANTES de procesar
    html_content = _clean_control_chars(html_content)
    
    if use_readability:
        try:
            doc = Document(html_content)
            cleaned = doc.summary()
            title = doc.title()
            
            # Si readability devuelve muy poco contenido, usar fallback
            if len(cleaned) < 200:
                logger.warning(f"Readability devolvió poco contenido ({len(cleaned)} chars), usando fallback")
                soup = BeautifulSoup(html_content, "html.parser")
                for tag in soup(["script", "style", "noscript", "iframe", "nav", "footer", "header"]):
                    tag.decompose()
                cleaned = str(soup.body) if soup.body else html_content
            
            return cleaned, title
        except Exception as e:
            logger.warning(f"Readability extraction failed: {e}")
    
    # Fallback: limpieza básica
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe", "nav", "footer", "header"]):
        tag.decompose()
    
    return str(soup.body) if soup.body else html_content, title


def simple_scrape(
    url: str,
    formats: Optional[List[str]] = None,
    only_main_content: bool = True,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    Scrapea una URL y la convierte a los formatos solicitados.
    
    API simple inspirada en Firecrawl para scraping web.
    
    Args:
        url: URL a scrapear
        formats: Lista de formatos a retornar. Opciones:
            - "markdown": Contenido convertido a Markdown (default)
            - "html": HTML limpio (contenido principal)
            - "rawHtml": HTML completo sin procesar
            - "links": Lista de URLs encontradas en la página
        only_main_content: Si True, usa readability para extraer solo contenido principal.
            Default True. Ideal para artículos, blogs, documentación.
        timeout: Timeout en segundos. Default 30.0
        
    Returns:
        Dict con estructura:
        {
            "success": True/False,
            "data": {
                "markdown": "# Título\\n\\nContenido...",
                "html": "<article>...</article>",
                "rawHtml": "<html>...</html>",
                "links": ["https://...", ...],
                "metadata": {
                    "title": "...",
                    "description": "...",
                    "sourceURL": "...",
                    ...
                }
            },
            "error": "mensaje de error si success=False"
        }
        
    Example:
        >>> result = simple_scrape("https://docs.firecrawl.dev")
        >>> if result["success"]:
        ...     print(result["data"]["markdown"][:500])
        
        >>> result = simple_scrape("https://example.com", formats=["markdown", "links"])
        >>> links = result["data"]["links"]
    """
    # Validar y normalizar formatos
    if formats is None:
        formats = ["markdown"]
    
    invalid_formats = set(formats) - SUPPORTED_FORMATS
    if invalid_formats:
        return {
            "success": False,
            "error": f"Formatos no soportados: {invalid_formats}. Válidos: {SUPPORTED_FORMATS}",
        }
    
    try:
        # Fetch de la página
        # verify=False para evitar errores de SSL en entornos corporativos con proxies
        with httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(timeout, connect=10.0),
            verify=False,
            http2=True,
        ) as client:
            response = client.get(url, headers=_get_headers())
            response.raise_for_status()
            
            # Manejar encoding
            if response.encoding:
                html_content = response.text
            else:
                html_content = response.content.decode("utf-8", errors="replace")
            
            status_code = response.status_code

    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"HTTP {e.response.status_code}: {str(e)}",
        }
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": f"Timeout después de {timeout}s",
        }
    except httpx.RequestError as e:
        return {
            "success": False,
            "error": f"Error de conexión: {str(e)}",
        }

    try:
        # Parse HTML
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Limpiar HTML y extraer título
        cleaned_html, article_title = _clean_html_for_markdown(html_content, use_readability=only_main_content)
        
        # Extraer metadata
        metadata = _extract_metadata(soup, url, status_code, article_title)
        
        # Construir respuesta
        data: Dict[str, Any] = {"metadata": metadata}
        
        if "rawHtml" in formats:
            data["rawHtml"] = html_content
            
        if "html" in formats:
            data["html"] = cleaned_html
            
        if "markdown" in formats:
            markdown_content = md(cleaned_html, heading_style="ATX")
            # Limpiar espacios excesivos
            markdown_content = "\n".join(line for line in markdown_content.split("\n") if line.strip())
            data["markdown"] = markdown_content.strip()
            
        if "links" in formats:
            data["links"] = _extract_links(soup, url)
        
        return {
            "success": True,
            "data": data,
        }

    except Exception as e:
        logger.error(f"Error procesando contenido de {url}: {e}")
        return {
            "success": False,
            "error": f"Error procesando contenido: {str(e)}",
        }

