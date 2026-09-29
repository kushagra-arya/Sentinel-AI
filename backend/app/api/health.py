"""Health-check endpoints for service and dependency readiness."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.health import HealthCheckResponse, ReadinessResponse
from app.services.health_service import HealthService

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Check backend liveness",
    description="Returns process liveness without requiring external dependencies.",
    openapi_extra={"x-roles": ["public"]},
)
async def health_check() -> HealthCheckResponse:
    """Return a liveness response for load balancers and operators."""
    return HealthService.liveness()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Check backend readiness",
    description="Verifies that required backend dependencies are reachable.",
    openapi_extra={"x-roles": ["public"]},
)
async def readiness_check(
    session: AsyncSession = Depends(get_db_session),
) -> ReadinessResponse:
    """Return dependency readiness, including the database connection."""
    return await HealthService.readiness(session)
