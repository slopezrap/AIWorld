"""
AIFoundry - Main Application

FastAPI application for AI agents and tools.
Uses the API router for all endpoints.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aifoundry.app.config import settings
from aifoundry.app.api.router import router as api_router


# ==============================================================================
# LIFESPAN (replaces deprecated @app.on_event)
# ==============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    Startup: Configura logging y verifica conectividad.
    Shutdown: Limpia recursos.
    """
    # STARTUP
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("🚀 AIFoundry API starting up...")
    logger.info(f"   LLM Model: {settings.litellm_model}")
    logger.info(f"   Brave MCP: {settings.brave_search_mcp_url}")
    logger.info(f"   Playwright MCP: {settings.playwright_mcp_url}")

    yield  # Application runs here

    # SHUTDOWN
    logger = logging.getLogger(__name__)
    logger.info("👋 AIFoundry API shutting down...")


# ==============================================================================
# APP
# ==============================================================================

app = FastAPI(
    title="AIFoundry API",
    description=(
        "API para agentes de IA que investigan la web.\n\n"
        "## Agentes disponibles\n"
        "- **electricity** — Precios de electricidad por proveedor/país\n"
        "- **salary** — Salarios por empresa/puesto/país\n"
        "- **social_comments** — Análisis de comentarios en redes sociales\n\n"
        "## Uso rápido\n"
        "```\n"
        'POST /agents/electricity/run {"provider": "Endesa", "country_code": "ES"}\n'
        "```"
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API router
app.include_router(api_router)


# ==============================================================================
# ROOT (redirect to docs)
# ==============================================================================


@app.get("/", tags=["root"], include_in_schema=False)
async def root():
    """Root endpoint — info básica del servicio."""
    return {
        "service": "AIFoundry API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "agents": "/agents",
    }


# ==============================================================================
# RUN
# ==============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "aifoundry.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )