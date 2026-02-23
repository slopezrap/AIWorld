"""
AIFoundry API Router.

Endpoints REST para gestionar y ejecutar agentes de IA.

Endpoints:
    GET  /health                    — Health check detallado
    GET  /agents                    — Lista agentes disponibles
    GET  /agents/{agent_name}/config — Devuelve config.json de un agente
    POST /agents/{agent_name}/run   — Ejecuta un agente
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from aifoundry.app.config import settings
from aifoundry.app.core.agents.scraper.agent import ScraperAgent
from aifoundry.app.core.agents.scraper.config_schema import AgentConfig
from aifoundry.app.schemas.agent_responses import get_response_schema
from aifoundry.app.utils.country import get_country_info

from .schemas import (
    AgentInfo,
    AgentListResponse,
    AgentRunRequest,
    AgentRunResponse,
    ErrorResponse,
    HealthResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# AGENT DISCOVERY
# =============================================================================

# Ruta base donde están los agentes (cada subdirectorio con config.json)
_AGENTS_DIR = Path(__file__).resolve().parent.parent / "core" / "agents"

# Meses en español (para query_template)
_MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


# Cache de configs validados (se llena en _discover_agents)
_validated_configs: Dict[str, AgentConfig] = {}


def _discover_agents() -> Dict[str, Dict[str, Any]]:
    """
    Descubre agentes disponibles buscando config.json recursivamente.

    Busca archivos config.json en cualquier subdirectorio de core/agents/.
    Usa el nombre del directorio padre del config.json como nombre del agente.
    Ignora directorios que empiezan con '_' o '__'.
    Valida cada config.json contra AgentConfig schema Pydantic.
    Los agentes con config inválido se descartan con un warning.

    Returns:
        Dict[agent_name, config_dict] con todos los agentes encontrados y válidos.
    """
    global _validated_configs
    agents: Dict[str, Dict[str, Any]] = {}

    if not _AGENTS_DIR.is_dir():
        logger.warning(f"Directorio de agentes no encontrado: {_AGENTS_DIR}")
        return agents

    for config_path in sorted(_AGENTS_DIR.glob("**/config.json")):
        agent_dir = config_path.parent
        agent_name = agent_dir.name

        # Ignorar directorios internos
        if agent_name.startswith("_"):
            continue

        try:
            with open(config_path) as f:
                raw_config = json.load(f)

            # Validar contra schema Pydantic
            validated = AgentConfig(**raw_config)
            _validated_configs[agent_name] = validated
            agents[agent_name] = raw_config
            logger.debug(
                f"Agent discovered: {agent_name} "
                f"(product={validated.product}, countries={validated.get_country_codes()})"
            )
        except ValidationError as e:
            logger.error(
                f"Config inválido para agente '{agent_name}' "
                f"({config_path}):\n{e}"
            )
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Error cargando config de {agent_name}: {e}")

    return agents


def get_validated_config(agent_name: str) -> AgentConfig | None:
    """Devuelve el AgentConfig validado de un agente, o None si no existe."""
    if not _validated_configs:
        _discover_agents()
    return _validated_configs.get(agent_name)


def _get_date_spanish() -> str:
    """Fecha actual en formato español: '14 enero 2026'."""
    now = datetime.now()
    return f"{now.day} {_MESES_ES[now.month]} {now.year}"


def _build_agent_config(
    agent_name: str,
    agent_config: Dict[str, Any],
    request: AgentRunRequest,
) -> Dict[str, Any]:
    """
    Construye el dict de config que se pasa a ScraperAgent.run().

    Combina el config.json del agente con los parámetros del request.
    Si no se proporciona query, la genera desde query_template.
    """
    country_code = request.country_code
    country_info = get_country_info(country_code)
    country_name = country_info.get("name", country_code)

    # Obtener language del config del agente o fallback
    countries = agent_config.get("countries", {})
    country_data = countries.get(country_code, {})
    language = country_data.get("language", "es")

    # Construir query
    if request.query:
        query = request.query
    else:
        template = agent_config.get(
            "query_template",
            "{product} {provider} {country_name}",
        )
        query = template.format(
            product=agent_config.get("product", agent_name),
            provider=request.provider,
            country_name=country_name,
            date=_get_date_spanish(),
        )

    config: Dict[str, Any] = {
        "product": agent_config.get("product", agent_name),
        "provider": request.provider,
        "country_code": country_code,
        "language": language,
        "query": query,
        "freshness": agent_config.get("freshness", "pw"),
        "extraction_prompt": agent_config.get("extraction_prompt", ""),
        "validation_prompt": agent_config.get("validation_prompt", ""),
    }

    # Thread ID para conversaciones multi-turn
    if request.thread_id:
        config["thread_id"] = request.thread_id

    return config


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Health check detallado",
)
async def health_check():
    """
    Devuelve el estado del servicio, modelo LLM configurado,
    URLs de MCPs y número de agentes disponibles.
    """
    agents = _discover_agents()
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        llm_model=settings.litellm_model,
        mcp_servers={
            "brave_search": settings.brave_search_mcp_url,
            "playwright": settings.playwright_mcp_url,
        },
        agents_available=len(agents),
    )


@router.get(
    "/agents",
    response_model=AgentListResponse,
    tags=["agents"],
    summary="Lista agentes disponibles",
)
async def list_agents():
    """
    Descubre y lista todos los agentes disponibles con su información básica.

    Escanea los subdirectorios de `core/agents/` buscando config.json.
    """
    agents = _discover_agents()
    agent_list: List[AgentInfo] = []

    for name, config in agents.items():
        countries_data = config.get("countries", {})
        providers_by_country = {
            cc: data.get("providers", [])
            for cc, data in countries_data.items()
        }

        agent_list.append(
            AgentInfo(
                name=name,
                product=config.get("product", name),
                countries=list(countries_data.keys()),
                providers_by_country=providers_by_country,
                has_extraction_prompt=bool(config.get("extraction_prompt")),
                has_validation_prompt=bool(config.get("validation_prompt")),
            )
        )

    return AgentListResponse(agents=agent_list, total=len(agent_list))


@router.get(
    "/agents/{agent_name}/config",
    response_model=Dict[str, Any],
    tags=["agents"],
    summary="Config de un agente",
    responses={404: {"model": ErrorResponse}},
)
async def get_agent_config(agent_name: str):
    """
    Devuelve el config.json completo de un agente específico.

    Útil para ver los providers, países, templates y prompts disponibles.
    """
    agents = _discover_agents()

    if agent_name not in agents:
        raise HTTPException(
            status_code=404,
            detail=f"Agente '{agent_name}' no encontrado. "
            f"Disponibles: {list(agents.keys())}",
        )

    return agents[agent_name]


@router.post(
    "/agents/{agent_name}/run",
    response_model=AgentRunResponse,
    tags=["agents"],
    summary="Ejecuta un agente",
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def run_agent(agent_name: str, request: AgentRunRequest):
    """
    Ejecuta un agente de investigación web.

    El agente:
    1. Construye queries de búsqueda basadas en el provider y país
    2. Busca en web vía Brave Search (si MCP habilitado)
    3. Scrapea las URLs encontradas
    4. Extrae y valida los datos según los prompts del config.json
    5. Devuelve el resultado estructurado

    **Ejemplo:**
    ```json
    POST /agents/electricity/run
    {
        "provider": "Endesa",
        "country_code": "ES"
    }
    ```
    """
    # Validar que el agente existe
    agents = _discover_agents()
    if agent_name not in agents:
        raise HTTPException(
            status_code=404,
            detail=f"Agente '{agent_name}' no encontrado. "
            f"Disponibles: {list(agents.keys())}",
        )

    agent_file_config = agents[agent_name]

    # Validar que el país está soportado (si el agente define countries)
    countries = agent_file_config.get("countries", {})
    if countries and request.country_code not in countries:
        raise HTTPException(
            status_code=422,
            detail=f"País '{request.country_code}' no soportado por '{agent_name}'. "
            f"Disponibles: {list(countries.keys())}",
        )

    # Construir config para el agente
    run_config = _build_agent_config(agent_name, agent_file_config, request)

    logger.info(
        f"Running agent '{agent_name}': provider={request.provider}, "
        f"country={request.country_code}, query='{run_config['query']}'"
    )

    # Ejecutar agente
    # Si structured_output=True, usar response_format nativo (1 sola llamada LLM)
    # en vez del post-procesamiento legacy (2 llamadas LLM).
    # Se infiere el schema Pydantic del product type del agente.
    response_model = None
    if request.structured_output:
        product = agent_file_config.get("product", agent_name)
        response_model = get_response_schema(product)
        logger.info(
            f"Using native response_format: {response_model.__name__} "
            f"(product={product})"
        )

    try:
        async with ScraperAgent(
            use_mcp=request.use_mcp,
            disable_simple_scrape=request.disable_simple_scrape,
            response_model=response_model,
            agent_name=agent_name,
            verbose=False,  # No verbose en API (usamos logging)
        ) as agent:
            result = await agent.run(run_config, max_retries=request.max_retries)
    except Exception as e:
        logger.error(f"Error ejecutando agente '{agent_name}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno ejecutando agente: {str(e)}",
        )

    # Serializar structured_response si es un objeto Pydantic
    structured = result.get("structured_response")
    if structured is not None and hasattr(structured, "model_dump"):
        structured = structured.model_dump()

    return AgentRunResponse(
        status=result.get("status", "error"),
        output=result.get("output", ""),
        messages_count=result.get("messages_count", 0),
        attempts=result.get("attempts", 1),
        thread_id=result.get("thread_id", ""),
        urls=result.get("urls", []),
        query_es=result.get("query_es", ""),
        query_final=result.get("query_final", ""),
        used_playwright=result.get("used_playwright", False),
        has_structured_output=result.get("has_structured_output", False),
        structured_response=structured,
    )