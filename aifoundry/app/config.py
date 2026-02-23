"""
AIFoundry - Configuration Module
Centraliza toda la configuración del proyecto usando Pydantic Settings.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración principal de AIFoundry."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===========================================
    # LiteLLM Configuration
    # ===========================================
    litellm_api_base: str = "https://api.openai.com/v1"
    litellm_api_key: str = ""
    litellm_model: str = "gpt-4o-mini"

    # ===========================================
    # Default LLM Settings
    # ===========================================
    default_temperature: float = 0.1
    default_max_tokens: int = 15000
    llm_num_retries: int = 3
    llm_request_timeout: int = 120

    # ===========================================
    # Database Configuration (futuro)
    # ===========================================
    database_url: Optional[str] = None

    # ===========================================
    # Vector Store Configuration (futuro)
    # ===========================================
    chroma_persist_directory: str = "./data/chroma"

    # ===========================================
    # MCP Servers Configuration
    # ===========================================
    brave_search_mcp_url: str = "http://localhost:8082/mcp"
    playwright_mcp_url: str = "http://localhost:8931/mcp"
    brave_api_key: str = ""  # API Key para Brave Search


@lru_cache
def get_settings() -> Settings:
    """
    Obtiene la instancia de Settings con cache.
    Usa lru_cache para singleton pattern.
    """
    return Settings()


# Instancia global para imports directos
settings = get_settings()
