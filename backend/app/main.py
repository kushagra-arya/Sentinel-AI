"""FastAPI application factory for SentinelAI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.dashboard import router as dashboard_router
from app.api.demo import router as demo_router
from app.api.health import router as health_router
from app.api.incidents import router as incidents_router
from app.api.map import router as map_router
from app.api.notifications import router as notifications_router
from app.api.risk import router as risk_router
from app.api.timeline import router as timeline_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Configure process-level services for the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("backend_starting", extra={"environment": settings.environment})
    yield
    logger.info("backend_stopping", extra={"environment": settings.environment})


def create_app() -> FastAPI:
    """Create and configure the SentinelAI API application."""
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title=settings.project_name,
        version="0.1.0",
        description=(
            "SentinelAI is an explainable industrial safety intelligence "
            "platform that fuses plant telemetry, work context, evidence "
            "links, retrieval-grounded guidance, and emergency workflows."
        ),
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url=f"{settings.api_v1_prefix}/docs",
        lifespan=lifespan,
    )
    app.include_router(auth_router, prefix=settings.api_v1_prefix)
    app.include_router(chat_router, prefix=settings.api_v1_prefix)
    app.include_router(dashboard_router, prefix=settings.api_v1_prefix)
    app.include_router(demo_router, prefix=settings.api_v1_prefix)
    app.include_router(health_router, prefix=settings.api_v1_prefix)
    app.include_router(incidents_router, prefix=settings.api_v1_prefix)
    app.include_router(map_router, prefix=settings.api_v1_prefix)
    app.include_router(notifications_router, prefix=settings.api_v1_prefix)
    app.include_router(risk_router, prefix=settings.api_v1_prefix)
    app.include_router(timeline_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
