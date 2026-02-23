"""
Schemas Pydantic para los endpoints de la API.

Define los modelos de request/response para la capa REST.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================


class AgentRunRequest(BaseModel):
    """Request para ejecutar un agente."""

    provider: str = Field(
        ...,
        description="Empresa/proveedor a investigar (ej: 'Endesa', 'H&M')",
        examples=["Endesa", "H&M", "Zara"],
    )
    country_code: str = Field(
        default="ES",
        description="Código de país ISO 3166-1 alpha-2",
        examples=["ES", "PT", "FR"],
    )
    query: Optional[str] = Field(
        default=None,
        description=(
            "Query personalizada. Si no se proporciona, se genera "
            "automáticamente desde el query_template del agente."
        ),
    )
    thread_id: Optional[str] = Field(
        default=None,
        description=(
            "Thread ID para reanudar una conversación previa. "
            "Si no se proporciona, se crea un nuevo thread."
        ),
    )
    structured_output: bool = Field(
        default=False,
        description="Si True, genera salida estructurada Pydantic vía LLM.",
    )
    use_mcp: bool = Field(
        default=True,
        description="Si True, usa herramientas MCP (Brave, Playwright).",
    )
    disable_simple_scrape: bool = Field(
        default=False,
        description="Si True, no incluye simple_scrape_url (fuerza Playwright).",
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Reintentos máximos ante errores de red.",
    )


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================


class AgentRunResponse(BaseModel):
    """Response de la ejecución de un agente."""

    status: str = Field(description="Estado: 'success' o 'error'")
    output: str = Field(default="", description="Output del agente en texto libre")
    messages_count: int = Field(default=0, description="Número de mensajes en la conversación")
    attempts: int = Field(default=1, description="Número de intentos realizados")
    thread_id: str = Field(default="", description="Thread ID de la conversación")
    urls: List[str] = Field(default_factory=list, description="URLs procesadas")
    query_es: str = Field(default="", description="Query en español utilizada")
    query_final: str = Field(default="", description="Query final utilizada")
    used_playwright: bool = Field(default=False, description="Si se usó Playwright")
    has_structured_output: bool = Field(
        default=False, description="Si hay structured_response"
    )
    structured_response: Optional[Dict[str, Any]] = Field(
        default=None, description="Respuesta estructurada (si se pidió)"
    )


class AgentInfo(BaseModel):
    """Información de un agente disponible."""

    name: str = Field(description="Nombre del directorio del agente")
    product: str = Field(description="Tipo de producto que investiga")
    countries: List[str] = Field(
        default_factory=list, description="Países soportados"
    )
    providers_by_country: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Proveedores disponibles por código de país",
    )
    has_extraction_prompt: bool = Field(
        default=False, description="Si tiene prompt de extracción personalizado"
    )
    has_validation_prompt: bool = Field(
        default=False, description="Si tiene prompt de validación personalizado"
    )


class AgentListResponse(BaseModel):
    """Response con la lista de agentes disponibles."""

    agents: List[AgentInfo] = Field(description="Agentes disponibles")
    total: int = Field(description="Total de agentes")


class HealthResponse(BaseModel):
    """Response del health check."""

    status: str = Field(description="Estado del servicio")
    version: str = Field(description="Versión de la API")
    llm_model: str = Field(description="Modelo LLM configurado")
    mcp_servers: Dict[str, str] = Field(
        description="URLs de los servidores MCP"
    )
    agents_available: int = Field(
        default=0, description="Número de agentes disponibles"
    )


class ErrorResponse(BaseModel):
    """Response de error estándar."""

    detail: str = Field(description="Descripción del error")