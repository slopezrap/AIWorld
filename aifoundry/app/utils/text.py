"""
Text Utilities - Funciones genéricas de procesamiento de texto.

Basado en HEFESTO - Utilidades genéricas reutilizables por cualquier agente.

Este módulo contiene funciones puras de procesamiento de texto:
- parse_json_response() - Parsea JSON de respuestas LLM
- extract_urls() - Extrae URLs de texto
- clean_markdown_code_blocks() - Limpia bloques de markdown
- truncate_text() - Trunca texto largo

NO contiene lógica específica de ningún agente.
"""

import json
import re
from typing import Any, Dict, List, Optional


def parse_json_response(text: Any) -> Optional[Dict[str, Any]]:
    """
    Parsea respuesta JSON que puede tener texto adicional alrededor.
    
    Útil para extraer JSON de respuestas de LLM que incluyen explicaciones.
    
    Args:
        text: Texto que contiene JSON (puede ser str, dict, o cualquier tipo)
        
    Returns:
        Dict parseado o None si no se encuentra JSON válido
        
    Example:
        >>> parse_json_response('Aquí está el resultado: {"precios": [...]}')
        {"precios": [...]}
        
        >>> parse_json_response('```json\\n{"key": "value"}\\n```')
        {"key": "value"}
    """
    if not text:
        return None
    
    # Si es un dict, extraer contenido relevante
    if isinstance(text, dict):
        if "raw_response" in text:
            text = text["raw_response"]
        elif "data" in text:
            data = text.get("data", {})
            if isinstance(data, dict) and "raw_response" in data:
                text = data["raw_response"]
            elif isinstance(data, str):
                text = data
    
    # Convertir a string si es necesario
    if not isinstance(text, str):
        try:
            text = str(text)
        except Exception:
            return None
    
    # Detectar respuestas vacías
    if "NO_DATA_FOUND" in text or "NOT_FOUND" in text:
        return None
    
    # Limpiar bloques de código markdown
    text = clean_markdown_code_blocks(text)
    
    # Buscar JSON en el texto
    json_match = re.search(r'\{[\s\S]*\}', text)
    if not json_match:
        return None
    
    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError:
        return None


def clean_markdown_code_blocks(text: str) -> str:
    """
    Elimina bloques de código markdown del texto.
    
    Args:
        text: Texto con posibles bloques ```json``` o ```
        
    Returns:
        Texto limpio sin delimitadores de código
    """
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    return text.strip()


def extract_urls(
    text: str,
    max_urls: int = 10,
    exclude_patterns: Optional[List[str]] = None
) -> List[str]:
    """
    Extrae URLs de un texto.
    
    Args:
        text: Texto que puede contener URLs
        max_urls: Máximo número de URLs a extraer
        exclude_patterns: Patrones a excluir (ej: ["google", "brave"])
    
    Returns:
        Lista de URLs únicas encontradas
        
    Example:
        >>> extract_urls("Visita https://iberdrola.es y https://google.com")
        ["https://iberdrola.es"]  # google excluido por defecto
    """
    # Patrones excluidos por defecto (motores de búsqueda, etc.)
    default_exclude = ["brave", "bing", "google.com/search", "duckduckgo"]
    exclude_patterns = exclude_patterns or default_exclude
    
    # Patrón de URL
    url_pattern = r'https?://[^\s\)\]\"\'\,<>]+'
    found_urls = re.findall(url_pattern, text)
    
    # Filtrar y deduplicar
    urls = []
    seen = set()
    
    for url in found_urls:
        # Limpiar puntuación al final
        url = url.rstrip('.')
        
        # Excluir patrones no deseados
        if any(pattern.lower() in url.lower() for pattern in exclude_patterns):
            continue
            
        # Evitar duplicados
        if url not in seen:
            seen.add(url)
            urls.append(url)
            
            if len(urls) >= max_urls:
                break
    
    return urls


def truncate_text(text: str, max_length: int = 5000, suffix: str = "...") -> str:
    """
    Trunca texto a un máximo de caracteres.
    
    Args:
        text: Texto a truncar
        max_length: Longitud máxima
        suffix: Sufijo a añadir si se trunca
        
    Returns:
        Texto truncado si excede el límite
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + suffix
