"""Health-check business logic for SentinelAI dependencies."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.health import HealthCheckResponse, ReadinessResponse


class HealthService:
    """Service methods for reporting application health."""

    @staticmethod
    def liveness() -> HealthCheckResponse:
        """Return a liveness result that does not depend on external services."""
        return HealthCheckResponse(status="ok", service="sentinelai-backend")

    @staticmethod
    async def readiness(session: AsyncSession) -> ReadinessResponse:
        """Check required dependencies and return a readiness result."""
        await session.execute(text("SELECT 1"))
        return ReadinessResponse(status="ready", database="reachable")
