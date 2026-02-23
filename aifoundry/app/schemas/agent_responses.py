"""
Esquemas de salida estructurada para agentes.

Define los formatos de respuesta que los agentes deben seguir.
Se usan con el parámetro response_format de create_agent para
forzar salidas estructuradas y validadas.

Uso:
    from aifoundry.app.schemas.agent_responses import SalaryResponse, ScraperResponse
    
    agent = create_agent(
        model=llm,
        tools=tools,
        response_format=SalaryResponse  # Fuerza formato estructurado
    )
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# =============================================================================
# ESQUEMA BASE PARA SCRAPER
# =============================================================================

class ScraperResponse(BaseModel):
    """Respuesta estructurada base del agente scraper."""
    
    query_es: str = Field(
        default="",
        description="Query de búsqueda en español"
    )
    query_final: str = Field(
        default="",
        description="Query final utilizada para la búsqueda"
    )
    urls: List[str] = Field(
        default_factory=list,
        description="URLs encontradas y procesadas"
    )
    used_playwright: bool = Field(
        default=False,
        description="Si se usó Playwright para scraping dinámico"
    )
    summary: str = Field(
        default="",
        description="Resumen de los hallazgos"
    )
    data_extracted: Dict[str, Any] = Field(
        default_factory=dict,
        description="Datos estructurados extraídos"
    )
    validation_status: str = Field(
        default="pending",
        description="Estado de validación: pending, valid, invalid"
    )
    validation_notes: str = Field(
        default="",
        description="Notas sobre la validación"
    )


# =============================================================================
# ESQUEMA PARA SALARIOS
# =============================================================================

class SalaryData(BaseModel):
    """Datos de salario extraídos."""
    
    position: str = Field(
        description="Puesto o cargo"
    )
    salary_min: Optional[float] = Field(
        default=None,
        description="Salario mínimo en euros/año o mes según se indique"
    )
    salary_max: Optional[float] = Field(
        default=None,
        description="Salario máximo en euros/año o mes según se indique"
    )
    salary_avg: Optional[float] = Field(
        default=None,
        description="Salario promedio"
    )
    salary_period: str = Field(
        default="year",
        description="Periodo del salario: year, month, hour"
    )
    currency: str = Field(
        default="EUR",
        description="Moneda"
    )
    source_url: Optional[str] = Field(
        default=None,
        description="URL fuente de los datos"
    )


class SalaryResponse(BaseModel):
    """Respuesta estructurada para consultas de salarios."""
    
    provider: str = Field(
        description="Empresa consultada (ej: H&M, Zara)"
    )
    country: str = Field(
        description="País de la consulta"
    )
    query_used: str = Field(
        description="Query de búsqueda utilizada"
    )
    salaries: List[SalaryData] = Field(
        default_factory=list,
        description="Lista de salarios encontrados por puesto"
    )
    sources: List[str] = Field(
        default_factory=list,
        description="URLs fuente consultadas"
    )
    summary: str = Field(
        description="Resumen ejecutivo de los hallazgos"
    )
    data_freshness: str = Field(
        default="unknown",
        description="Antigüedad de los datos: recent (< 6 meses), old (> 1 año), unknown"
    )
    confidence: str = Field(
        default="medium",
        description="Nivel de confianza: high, medium, low"
    )
    notes: str = Field(
        default="",
        description="Notas adicionales o advertencias"
    )


# =============================================================================
# REGISTRO DE ESQUEMAS POR TIPO DE AGENTE
# =============================================================================

RESPONSE_SCHEMAS = {
    "salary": SalaryResponse,
    "salarios": SalaryResponse,
    "default": ScraperResponse,
}


def get_response_schema(product_type: str) -> type[BaseModel]:
    """
    Obtiene el esquema de respuesta según el tipo de producto.
    
    Args:
        product_type: Tipo de producto (salary, electricity, etc)
        
    Returns:
        Clase Pydantic del esquema correspondiente
    """
    return RESPONSE_SCHEMAS.get(product_type.lower(), ScraperResponse)
