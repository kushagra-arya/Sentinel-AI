"""Operational map API routes."""

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import require_roles
from app.models.enums import UserRole
from app.models.users import User
from app.schemas.map import (
    AlertMarkerResponse,
    HazardZoneCreate,
    MapMarker,
    MapViewportRequest,
    MapViewportResponse,
    PlantLayoutCreate,
    PlantLayoutResponse,
)
from app.services.map_service import MapService

router = APIRouter(prefix="/map", tags=["map"])


@router.post(
    "/layouts",
    response_model=PlantLayoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create plant layout",
    description="Stores image or georeferenced plant layout metadata for map clients.",
    openapi_extra={"x-roles": ["admin", "safety_officer"]},
)
async def create_layout(
    payload: PlantLayoutCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SAFETY_OFFICER)),
    session: AsyncSession = Depends(get_db_session),
) -> PlantLayoutResponse:
    """Create active plant layout metadata."""
    return await MapService.create_layout(
        session,
        payload=payload,
        actor_user_id=current_user.id,
    )


@router.get(
    "/layouts/{plant_id}",
    response_model=PlantLayoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Get active plant layout",
    description="Returns active layout metadata without dynamic markers or heatmap layers.",
    openapi_extra={
        "x-roles": ["admin", "safety_officer", "supervisor", "compliance_officer", "viewer"]
    },
)
async def get_layout(
    plant_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$"),
    _current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.SAFETY_OFFICER,
            UserRole.SUPERVISOR,
            UserRole.COMPLIANCE_OFFICER,
            UserRole.VIEWER,
        )
    ),
    session: AsyncSession = Depends(get_db_session),
) -> PlantLayoutResponse:
    """Return active layout metadata for a plant."""
    return await MapService.get_layout(session, plant_id=plant_id)


@router.post(
    "/hazards",
    response_model=MapMarker,
    status_code=status.HTTP_201_CREATED,
    summary="Create hazard zone",
    description="Stores hazard-zone geometry for operational map overlays.",
    openapi_extra={"x-roles": ["admin", "safety_officer"]},
)
async def create_hazard_zone(
    payload: HazardZoneCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SAFETY_OFFICER)),
    session: AsyncSession = Depends(get_db_session),
) -> MapMarker:
    """Create a hazard-zone marker layer."""
    return await MapService.create_hazard_zone(
        session,
        payload=payload,
        actor_user_id=current_user.id,
    )


@router.post(
    "/viewport",
    response_model=MapViewportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dynamic map viewport layers",
    description="Returns requested dynamic markers and computed heatmap without refetching layout.",
    openapi_extra={
        "x-roles": ["admin", "safety_officer", "supervisor", "compliance_officer", "viewer"]
    },
)
async def get_viewport(
    payload: MapViewportRequest,
    _current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.SAFETY_OFFICER,
            UserRole.SUPERVISOR,
            UserRole.COMPLIANCE_OFFICER,
            UserRole.VIEWER,
        )
    ),
    session: AsyncSession = Depends(get_db_session),
) -> MapViewportResponse:
    """Return dynamic viewport map layers."""
    return await MapService.get_viewport(session, payload=payload)


@router.get(
    "/alerts/{plant_id}",
    response_model=list[AlertMarkerResponse],
    status_code=status.HTTP_200_OK,
    summary="Get evidence-positioned alert markers",
    description="Positions alerts from their evidence chain, preferring source sensor locations.",
    openapi_extra={
        "x-roles": ["admin", "safety_officer", "supervisor", "compliance_officer", "viewer"]
    },
)
async def get_alert_markers(
    plant_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$"),
    _current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.SAFETY_OFFICER,
            UserRole.SUPERVISOR,
            UserRole.COMPLIANCE_OFFICER,
            UserRole.VIEWER,
        )
    ),
    session: AsyncSession = Depends(get_db_session),
) -> list[AlertMarkerResponse]:
    """Return alert markers positioned by evidence records."""
    return await MapService.alert_markers(session, plant_id=plant_id)
