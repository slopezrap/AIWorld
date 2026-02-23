"""
Country Utilities - Información genérica de países.

Contiene solo información común a TODOS los agentes:
- Nombre, moneda, idioma, código Brave

Info específica (electricidad, salarios) va en cada agente.
"""

from typing import Dict, Any


# Información GENÉRICA de países (compartida por todos los agentes)
COUNTRY_INFO: Dict[str, Dict[str, Any]] = {
    "ES": {
        "name": "España",
        "country_name": "España",
        "currency": "EUR",
        "currency_symbol": "€",
        "language": "es",
    },
    "PT": {
        "name": "Portugal",
        "country_name": "Portugal",
        "currency": "EUR",
        "currency_symbol": "€",
        "language": "pt",
    },
    "FR": {
        "name": "Francia",
        "country_name": "France",
        "currency": "EUR",
        "currency_symbol": "€",
        "language": "fr",
    },
    "DE": {
        "name": "Alemania",
        "country_name": "Deutschland",
        "currency": "EUR",
        "currency_symbol": "€",
        "language": "de",
    },
    "IT": {
        "name": "Italia",
        "country_name": "Italia",
        "currency": "EUR",
        "currency_symbol": "€",
        "language": "it",
    },
    "UK": {
        "name": "Reino Unido",
        "country_name": "United Kingdom",
        "currency": "GBP",
        "currency_symbol": "£",
        "language": "en",
    },
    "NL": {
        "name": "Países Bajos",
        "country_name": "Nederland",
        "currency": "EUR",
        "currency_symbol": "€",
        "language": "nl",
    },
    "BE": {
        "name": "Bélgica",
        "country_name": "België/Belgique",
        "currency": "EUR",
        "currency_symbol": "€",
        "language": "nl",
    },
    "PL": {
        "name": "Polonia",
        "country_name": "Polska",
        "currency": "PLN",
        "currency_symbol": "zł",
        "language": "pl",
    },
    "US": {
        "name": "Estados Unidos",
        "country_name": "United States",
        "currency": "USD",
        "currency_symbol": "$",
        "language": "en",
    },
}

# Mapping ISO -> Brave country codes
BRAVE_COUNTRY_CODES: Dict[str, str] = {
    "UK": "GB",
    "ES": "ES",
    "US": "US",
    "DE": "DE",
    "FR": "FR",
    "IT": "IT",
    "PT": "PT",
    "NL": "NL",
    "BE": "BE",
    "PL": "PL",
}

# Mapping para Brave search_lang (idioma de búsqueda)
# Formato: idioma simple -> código Brave válido
BRAVE_SEARCH_LANG: Dict[str, str] = {
    "es": "es",
    "pt": "pt-pt",  # Brave no acepta "pt", requiere "pt-pt" o "pt-br"
    "en": "en",
    "fr": "fr",
    "de": "de",
    "it": "it",
    "nl": "nl",
    "pl": "pl",
}

# Mapping para Brave ui_lang (idioma de interfaz) - formato: país -> ui_lang
# Brave requiere formato específico como "es-ES", "pt-BR", etc.
BRAVE_UI_LANG: Dict[str, str] = {
    "ES": "es-ES",
    "PT": "pt-BR",  # Brave no tiene pt-PT, usa pt-BR
    "FR": "fr-FR",
    "DE": "de-DE",
    "IT": "it-IT",
    "UK": "en-GB",
    "US": "en-US",
    "NL": "nl-NL",
    "BE": "nl-BE",
    "PL": "pl-PL",
}


def get_country_info(country_code: str) -> Dict[str, Any]:
    """
    Obtiene información genérica de un país.
    
    Args:
        country_code: Código ISO del país (ej: "ES", "UK")
        
    Returns:
        Dict con name, currency, language, etc.
    """
    country_code = country_code.upper()
    
    if country_code in COUNTRY_INFO:
        return COUNTRY_INFO[country_code].copy()
    
    # Valores por defecto para países no configurados
    return {
        "name": country_code,
        "country_name": country_code,
        "currency": "EUR",
        "currency_symbol": "€",
        "language": "en",
    }


def get_brave_country_code(iso_code: str) -> str:
    """
    Convierte código ISO de país a código Brave.
    
    Args:
        iso_code: Código ISO del país (ej: "UK", "ES")
        
    Returns:
        Código Brave correspondiente (ej: "GB", "ES")
    """
    return BRAVE_COUNTRY_CODES.get(iso_code.upper(), iso_code.upper())


def get_currency_info(country_code: str) -> Dict[str, str]:
    """
    Obtiene información de la moneda de un país.
    
    Args:
        country_code: Código ISO del país
        
    Returns:
        Dict con currency y symbol
    """
    info = get_country_info(country_code)
    return {
        "currency": info.get("currency", "EUR"),
        "symbol": info.get("currency_symbol", "€")
    }


def get_brave_search_lang(language: str) -> str:
    """
    Obtiene el código de idioma válido para Brave search_lang.
    
    Args:
        language: Código de idioma simple (ej: "pt", "es")
        
    Returns:
        Código Brave válido (ej: "pt-pt", "es")
    """
    return BRAVE_SEARCH_LANG.get(language.lower(), "en")


def get_brave_ui_lang(country_code: str) -> str:
    """
    Obtiene el código ui_lang válido para Brave.
    
    Args:
        country_code: Código ISO del país (ej: "PT", "ES")
        
    Returns:
        Código Brave ui_lang (ej: "pt-BR", "es-ES")
    """
    return BRAVE_UI_LANG.get(country_code.upper(), "en-US")


def get_brave_config(country_code: str) -> Dict[str, str]:
    """
    Obtiene toda la config necesaria para Brave Search.
    
    Args:
        country_code: Código ISO del país
        
    Returns:
        Dict con country, search_lang, ui_lang para Brave
    """
    info = get_country_info(country_code)
    language = info.get("language", "en")
    
    return {
        "country": get_brave_country_code(country_code),
        "search_lang": get_brave_search_lang(language),
        "ui_lang": get_brave_ui_lang(country_code),
    }
