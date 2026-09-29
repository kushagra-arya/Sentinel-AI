"""Forensic timeline API routes."""

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import require_roles
from app.models.enums import UserRole
from app.models.users import User
from app.schemas.timeline import TimelineResponse
from app.services.timeline_service import TimelineService

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get(
    "/incidents/{incident_id}",
    response_model=TimelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Reconstruct incident timeline",
    description="Builds a chronological timeline from stored incident evidence links.",
    openapi_extra={"x-roles": ["admin", "safety_officer", "supervisor", "compliance_officer"]},
)
async def get_incident_timeline(
    incident_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$"),
    _current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.SAFETY_OFFICER,
            UserRole.SUPERVISOR,
            UserRole.COMPLIANCE_OFFICER,
        )
    ),
    session: AsyncSession = Depends(get_db_session),
) -> TimelineResponse:
    """Return an incident timeline reconstructed from evidence links."""
    return await TimelineService.for_incident(session, incident_id=incident_id)


@router.get(
    "/alerts/{alert_id}",
    response_model=TimelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Reconstruct alert timeline",
    description="Builds a chronological alert timeline from stored alert evidence links.",
    openapi_extra={"x-roles": ["admin", "safety_officer", "supervisor", "compliance_officer"]},
)
async def get_alert_timeline(
    alert_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$"),
    _current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.SAFETY_OFFICER,
            UserRole.SUPERVISOR,
            UserRole.COMPLIANCE_OFFICER,
        )
    ),
    session: AsyncSession = Depends(get_db_session),
) -> TimelineResponse:
    """Return an alert timeline reconstructed from evidence links."""
    return await TimelineService.for_alert(session, alert_id=alert_id)
