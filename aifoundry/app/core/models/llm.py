"""
AIFoundry - LLM Factory Module
============================
Patrón Singleton para instancia de LLM compartida.
Usa init_chat_model de LangChain (API moderna) apuntando al proxy LiteLLM.
"""

from typing import Optional
from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel
from aifoundry.app.config import settings
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# SINGLETON LLM
# =============================================================================
# Una única instancia de LLM compartida en toda la aplicación.
# Esto cumple con la arquitectura donde el AGENTE es el único "dueño" del LLM,
# pero otros módulos pueden acceder a la misma instancia si es necesario.

_llm_instance: Optional[BaseChatModel] = None


def get_llm(
    model_name: Optional[str] = None, 
    temperature: Optional[float] = None
) -> BaseChatModel:
    """
    Retorna la instancia singleton de LangChain ChatModel.
    
    ARQUITECTURA:
    - Primera llamada: crea la instancia usando init_chat_model (API moderna)
    - Llamadas siguientes: retorna la misma instancia
    
    Utiliza la configuración definida en settings (api_key, base_url, model).
    El modelo usa el proxy LiteLLM que es OpenAI-compatible.
    
    Args:
        model_name: Nombre del modelo (opcional, usa LITELLM_MODEL por defecto)
        temperature: Temperatura para generación (opcional, usa DEFAULT_TEMPERATURE)
    
    Returns:
        BaseChatModel: Instancia configurada de LangChain Chat Model
    """
    global _llm_instance
    
    # Si ya existe la instancia, retornarla (singleton)
    if _llm_instance is not None:
        return _llm_instance
    
    model = model_name or settings.litellm_model
    temp = temperature if temperature is not None else settings.default_temperature
    
    num_retries = settings.llm_num_retries
    request_timeout = settings.llm_request_timeout
    
    logger.info(f"🚀 Inicializando LLM SINGLETON (init_chat_model)")
    logger.info(f"   📍 Base URL: {settings.litellm_api_base}")
    logger.info(f"   🤖 Modelo: {model}")
    logger.info(f"   🌡️ Temperature: {temp}")
    logger.info(f"   🔄 Retries: {num_retries}, ⏱️ Timeout: {request_timeout}s")
    
    # Configurar headers adicionales - User-Agent COMPLETO requerido por api.inditex.com
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }
    logger.info("   🛡️ Headers configurados (User-Agent completo para WAF)")

    # Crear instancia única usando init_chat_model (API moderna de LangChain)
    # Detectamos el provider del modelo para usar init_chat_model correctamente
    # Para modelos via LiteLLM proxy, usamos model_provider="openai" ya que es compatible
    _llm_instance = init_chat_model(
        model=model,
        model_provider="openai",  # LiteLLM proxy es OpenAI-compatible
        temperature=temp,
        max_tokens=settings.default_max_tokens,
        api_key=settings.litellm_api_key,
        base_url=settings.litellm_api_base,
        default_headers=default_headers,
        max_retries=num_retries,
        timeout=request_timeout,
    )
    
    logger.info("   ✅ LLM SINGLETON inicializado correctamente (init_chat_model)")
    
    return _llm_instance


def reset_llm() -> None:
    """
    Resetea el singleton (útil para tests o reconfiguración).
    """
    global _llm_instance
    _llm_instance = None
    logger.info("🔄 LLM SINGLETON reseteado")
