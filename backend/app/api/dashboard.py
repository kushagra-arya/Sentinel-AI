"""Dashboard aggregation API routes."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import require_roles
from app.models.enums import UserRole
from app.models.users import User
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummary,
    status_code=status.HTTP_200_OK,
    summary="Get command-center dashboard summary",
    description=(
        "Returns current risk, alert, workforce, permit, maintenance, telemetry, "
        "equipment, incident, and live-feed aggregates in one optimized call."
    ),
    openapi_extra={
        "x-roles": ["admin", "safety_officer", "supervisor", "compliance_officer", "viewer"]
    },
)
async def get_dashboard_summary(
    plant_id: str = Query(description="Plant identifier to aggregate."),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.SAFETY_OFFICER,
            UserRole.SUPERVISOR,
            UserRole.COMPLIANCE_OFFICER,
            UserRole.VIEWER,
        )
    ),
    session: AsyncSession = Depends(get_db_session),
) -> DashboardSummary:
    """Return a single-call dashboard summary for an authorized user."""
    del current_user
    return await DashboardService.get_summary(session, plant_id=plant_id)
