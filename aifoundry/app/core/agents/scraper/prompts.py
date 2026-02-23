"""
System prompts para agentes de scraping - BASE.

Los pasos son iguales para todos los dominios.
Solo cambia la config que se inyecta (product, provider, country...).

Opcionalmente, cada dominio puede incluir extraction_prompt y validation_prompt
en su config.json para personalizar los pasos 6 y 7.
"""

from datetime import datetime
from typing import Optional

from aifoundry.app.utils.country import get_country_info, get_brave_config

# Meses en español
MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}

# Nombres de idiomas
LANGUAGE_NAMES = {
    "es": "español",
    "pt": "portugués",
    "fr": "francés",
    "de": "alemán",
    "it": "italiano",
    "en": "inglés",
    "nl": "neerlandés",
    "pl": "polaco",
}


def get_date_spanish() -> str:
    """Genera la fecha actual en formato español: '13 enero 2026'."""
    now = datetime.now()
    return f"{now.day} {MESES_ES[now.month]} {now.year}"


def get_system_prompt(config: dict) -> str:
    """
    Genera el system prompt para un agente de scraping.
    
    Si el config incluye 'system_prompt_template', lo usa como prompt custom
    con sustitución de variables. Si no, usa el prompt genérico de 7 pasos.
    
    Variables disponibles en system_prompt_template:
        {product}, {provider}, {provider_text}, {country_name}, {country_code},
        {language}, {language_name}, {date}, {freshness}, {query_es},
        {brave_search_lang}, {brave_ui_lang}, {brave_country},
        {extraction_prompt}, {validation_prompt},
        {extraction_section}, {validation_section}
    
    Args:
        config: Dict con product, provider, country_code, language, date, etc.
        
    Returns:
        System prompt con la config inyectada
    """
    # Extraer config con defaults
    product = config.get("product", "producto")
    provider = config.get("provider", "")
    country_code = config.get("country_code", "ES")
    language = config.get("language", "es")
    date = config.get("date") or get_date_spanish()
    freshness = config.get("freshness", "py")  # py = past year
    
    # Obtener nombres legibles
    country_info = get_country_info(country_code)
    country_name = country_info["name"]
    language_name = LANGUAGE_NAMES.get(language, language)
    
    # Provider text (puede estar vacío)
    provider_text = f"de {provider} " if provider else ""
    
    # Query: usar del config si existe, sino construir default
    default_query = f"precio de {product} {provider_text}en {country_name} en {date}"
    query_es = config.get("query") or default_query
    
    # Config Brave (códigos específicos)
    brave_cfg = get_brave_config(country_code)
    brave_search_lang = brave_cfg["search_lang"]
    brave_ui_lang = brave_cfg["ui_lang"]
    brave_country = brave_cfg["country"]
    
    # Prompts opcionales específicos del dominio (vienen del config.json)
    extraction_prompt = config.get("extraction_prompt", "")
    validation_prompt = config.get("validation_prompt", "")
    
    extraction_section = ""
    if extraction_prompt:
        extraction_section = f"\nINSTRUCCIONES ESPECÍFICAS DE EXTRACCIÓN PARA {product.upper()}:\n{extraction_prompt}"
    
    validation_section = ""
    if validation_prompt:
        validation_section = f"\nVALIDACIONES ESPECÍFICAS PARA {product.upper()}:\n{validation_prompt}"
    
    # --- CHECK: ¿Tiene el agente un system_prompt_template custom? ---
    custom_template = config.get("system_prompt_template")
    if custom_template:
        try:
            return custom_template.format(
                product=product,
                provider=provider,
                provider_text=provider_text,
                country_name=country_name,
                country_code=country_code,
                language=language,
                language_name=language_name,
                date=date,
                freshness=freshness,
                query_es=query_es,
                brave_search_lang=brave_search_lang,
                brave_ui_lang=brave_ui_lang,
                brave_country=brave_country,
                extraction_prompt=extraction_prompt,
                validation_prompt=validation_prompt,
                extraction_section=extraction_section,
                validation_section=validation_section,
            )
        except KeyError as e:
            # Si el template tiene una variable no reconocida, fallback al genérico
            import logging
            logging.getLogger(__name__).warning(
                f"Variable desconocida en system_prompt_template: {e}. "
                f"Usando prompt genérico."
            )
    
    # --- PROMPT GENÉRICO OPTIMIZADO (fallback) ---
    
    # Instrucción de traducción (implícita, no es un paso separado)
    translate_hint = ""
    if language != "es":
        translate_hint = f"\nTraducción: traduce la query al {language_name} antes de buscar.\n"
    
    return f"""Eres un agente de investigación web. Buscas, scrapeas y extraes datos estructurados.

CONFIGURACIÓN:
• Producto: {product} | Proveedor: {provider or "(genérico)"} | País: {country_name} ({country_code})
• Idioma: {language_name} | Fecha: {date}
• Query: "{query_es}"
{translate_hint}
═══ PASO 1: BUSCAR CON BRAVE ═══

brave_web_search(query="...", count=20, freshness="{freshness}", search_lang="{brave_search_lang}", ui_lang="{brave_ui_lang}", country="{brave_country}")

Códigos obligatorios: freshness="{freshness}", search_lang="{brave_search_lang}", ui_lang="{brave_ui_lang}", country="{brave_country}".
{"Busca con la query en español tal cual." if language == "es" else f"Traduce la query al {language_name} antes de buscar."}

═══ PASO 2: SELECCIONAR Y SCRAPEAR ═══

De los 20 resultados, selecciona las **5-8 URLs más relevantes** según título y descripción.

Criterios de selección (priorizar):
1. Fuentes oficiales (gobierno, reguladores, empresas)
2. Portales especializados del sector
3. Medios de comunicación reconocidos
Evitar: foros, blogs personales, aggregadores sin fuente original.

Scrapea cada URL seleccionada con `simple_scrape_url(url="...")`.
Si una URL falla, continúa con la siguiente.

═══ PASO 3: PLAYWRIGHT (fallback) ═══

Si alguna URL relevante falló en el paso 2 (SSL, bloqueo, timeout), usa Playwright:
- Acepta cookies si aparecen
- Si 403/bloqueado, pasa a la siguiente
- Si la página es dinámica, espera a que cargue

Solo usa Playwright para URLs fallidas. Si todas funcionaron, salta este paso.

REGLA DE PARADA: Si tras procesar 8 URLs no encuentras datos relevantes sobre {product} {provider_text}en {country_name}, para y reporta que no se encontraron datos suficientes.

═══ PASO 4: EXTRACCIÓN ═══

De todo el contenido scrapeado, extrae datos estructurados:
- URL, método (simple_scrape/playwright), datos relevantes para {product} {provider_text}
{extraction_section}

═══ PASO 5: VALIDACIÓN Y RESULTADO ═══

Valida antes de presentar:
✓ ≥1 fuente con datos | ✓ Datos corresponden a {product} | ✓ País: {country_name} | ✓ Fecha cercana a {date}

Incluye al final:
```
VALIDACIÓN:
- Fuentes procesadas: [X] | Con datos: [Y]
- Status: ✅ VÁLIDO | ⚠️ PARCIAL | ❌ INVÁLIDO
- Comentarios: [razón]
```
{validation_section}

═══ RESUMEN ═══
1. Buscar con Brave (20 resultados)
2. Seleccionar 5-8 mejores URLs → scrapear con simple_scrape_url
3. Playwright para URLs fallidas (si las hay)
4. Extraer datos estructurados
5. Validar y presentar resultado

"""
