"""Incident emergency response and report generation API routes."""

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import require_roles
from app.models.enums import UserRole
from app.models.users import User
from app.schemas.incidents import (
    EmergencyPanelState,
    ExportResponse,
    IncidentReport,
    ReportStubResponse,
)
from app.services.report_service import ReportService

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get(
    "/{incident_id}/emergency-panel",
    response_model=EmergencyPanelState,
    status_code=status.HTTP_200_OK,
    summary="Get emergency response panel state",
    description=(
        "Computes live response state from incident evidence, "
        "workers, equipment, and rules."
    ),
    openapi_extra={"x-roles": ["admin", "safety_officer", "supervisor"]},
)
async def get_emergency_panel(
    incident_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$"),
    _current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.SAFETY_OFFICER, UserRole.SUPERVISOR)
    ),
    session: AsyncSession = Depends(get_db_session),
) -> EmergencyPanelState:
    """Return live emergency response panel state."""
    return await ReportService.emergency_panel(session, incident_id=incident_id)


@router.get(
    "/{incident_id}/report",
    response_model=IncidentReport,
    status_code=status.HTTP_200_OK,
    summary="Generate incident report",
    description="Generates an incident report from evidence links and timeline reconstruction.",
    openapi_extra={"x-roles": ["admin", "safety_officer", "supervisor", "compliance_officer"]},
)
async def get_incident_report(
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
) -> IncidentReport:
    """Return generated incident report content."""
    return await ReportService.incident_report(session, incident_id=incident_id)


@router.get(
    "/{incident_id}/report.csv",
    response_model=ExportResponse,
    status_code=status.HTTP_200_OK,
    summary="Export incident report as CSV",
    description="Exports the generated incident report evidence and timeline as CSV.",
    openapi_extra={"x-roles": ["admin", "safety_officer", "compliance_officer"]},
)
async def export_incident_csv(
    incident_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$"),
    _current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.SAFETY_OFFICER, UserRole.COMPLIANCE_OFFICER)
    ),
    session: AsyncSession = Depends(get_db_session),
) -> ExportResponse:
    """Return a base64 CSV incident report export."""
    return await ReportService.export_incident_csv(session, incident_id=incident_id)


@router.get(
    "/{incident_id}/report.pdf",
    response_model=ExportResponse,
    status_code=status.HTTP_200_OK,
    summary="Export incident report as PDF",
    description="Exports the generated incident report as a PDF suitable for audit review.",
    openapi_extra={"x-roles": ["admin", "safety_officer", "compliance_officer"]},
)
async def export_incident_pdf(
    incident_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$"),
    _current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.SAFETY_OFFICER, UserRole.COMPLIANCE_OFFICER)
    ),
    session: AsyncSession = Depends(get_db_session),
) -> ExportResponse:
    """Return a base64 PDF incident report export."""
    return await ReportService.export_incident_pdf(session, incident_id=incident_id)


@router.get(
    "/reports/{report_type}",
    response_model=ReportStubResponse,
    status_code=status.HTTP_200_OK,
    summary="Get future report export status",
    description="Shows how future report types will reuse the incident report export pipeline.",
    openapi_extra={"x-roles": ["admin", "safety_officer", "compliance_officer"]},
)
async def get_report_stub(
    report_type: str = Path(
        min_length=1,
        max_length=80,
        pattern=(
            r"^(daily-safety|incident|risk-trend|equipment-risk|permit-summary|"
            r"compliance-summary)$"
        ),
    ),
    _current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.SAFETY_OFFICER, UserRole.COMPLIANCE_OFFICER)
    ),
) -> ReportStubResponse:
    """Return stub status for future report types."""
    return ReportService.stub_report(report_type)
