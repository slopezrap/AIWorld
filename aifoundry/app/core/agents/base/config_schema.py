"""
Schema Pydantic para validar config.json de agentes.

Cada agente tiene un config.json con la estructura definida por AgentConfig.
Este schema se usa para:
1. Validar configs al cargar (errores claros si falta algo)
2. Detectar typos con extra="forbid"
3. Documentar la estructura esperada

Ejemplos de config.json válidos:
    - electricity/config.json (con extraction_prompt, validation_prompt, providers)
    - salary/config.json (sin prompts custom, con providers)
    - social_comments/config.json (con social_networks, sin providers)
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class CountryConfig(BaseModel):
    """Configuración por país dentro de un agente."""

    model_config = ConfigDict(extra="forbid")

    language: str
    providers: List[str] = []

    @field_validator("language")
    @classmethod
    def language_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("language no puede estar vacío")
        return v.strip().lower()


class AgentConfig(BaseModel):
    """
    Schema principal para config.json de agentes.

    Campos requeridos:
        - product: Nombre del producto/dominio (ej: "electricidad", "salarios")
        - query_template: Template para generar queries de búsqueda
        - countries: Dict de código ISO → configuración del país

    Campos opcionales:
        - freshness: Filtro de frescura para Brave Search (default "pw" = semana pasada)
        - extraction_prompt: Prompt custom para el paso de extracción de datos
        - validation_prompt: Prompt custom para el paso de validación
        - social_networks: Lista de redes sociales (solo para agente social_comments)
    """

    model_config = ConfigDict(extra="forbid")

    product: str
    query_template: str
    countries: Dict[str, CountryConfig]
    freshness: str = "pw"
    extraction_prompt: str = ""
    validation_prompt: str = ""
    system_prompt_template: Optional[str] = None
    social_networks: Optional[List[str]] = None

    @field_validator("product")
    @classmethod
    def product_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("product no puede estar vacío")
        return v.strip()

    @field_validator("query_template")
    @classmethod
    def query_template_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query_template no puede estar vacío")
        return v.strip()

    @field_validator("countries")
    @classmethod
    def at_least_one_country(cls, v: Dict[str, CountryConfig]) -> Dict[str, CountryConfig]:
        if not v:
            raise ValueError("countries debe tener al menos un país")
        return v

    @field_validator("freshness")
    @classmethod
    def valid_freshness(cls, v: str) -> str:
        """Valida que freshness sea un valor reconocido por Brave Search."""
        valid = {"pd", "pw", "pm", "py", ""}
        if v not in valid:
            raise ValueError(
                f"freshness '{v}' no válido. Opciones: pd (día), pw (semana), "
                f"pm (mes), py (año), '' (sin filtro)"
            )
        return v

    def get_country_codes(self) -> List[str]:
        """Lista de códigos de país soportados."""
        return list(self.countries.keys())

    def get_providers(self, country_code: str) -> List[str]:
        """Providers para un país específico."""
        country = self.countries.get(country_code)
        return country.providers if country else []

    def get_language(self, country_code: str) -> str:
        """Idioma para un país específico."""
        country = self.countries.get(country_code)
        return country.language if country else "es"