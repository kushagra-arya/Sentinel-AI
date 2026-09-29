"""Demo replay control API for the unattended Section 15 flow."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.schemas.demo import (
    DemoAdvanceRequest,
    DemoPerformanceResponse,
    DemoStartRequest,
    DemoStatusResponse,
)
from app.services.demo_service import DemoService

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post(
    "/replay/start",
    response_model=DemoStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Start deterministic demo replay",
    description="Resets demo data and starts the Section 15 replay controller.",
    openapi_extra={"x-roles": ["public"]},
)
async def start_demo_replay(
    payload: DemoStartRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> DemoStatusResponse:
    """Reset and start the deterministic end-to-end demo replay."""
    return await DemoService.start(
        session,
        settings=settings,
        mode=payload.mode,
        speed_multiplier=payload.speed_multiplier,
    )


@router.post(
    "/replay/advance",
    response_model=DemoStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Advance deterministic demo replay",
    description="Advances the replay to a requested Section 15 demo step.",
    openapi_extra={"x-roles": ["public"]},
)
async def advance_demo_replay(
    payload: DemoAdvanceRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> DemoStatusResponse:
    """Advance the replay to a specific demo step."""
    return await DemoService.advance(session, settings=settings, target_step=payload.step)


@router.get(
    "/replay/status",
    response_model=DemoStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get deterministic demo replay status",
    description="Returns current replay step and stable demo entity identifiers.",
    openapi_extra={"x-roles": ["public"]},
)
async def get_demo_replay_status() -> DemoStatusResponse:
    """Return current deterministic demo replay status."""
    return DemoService.status()


@router.get(
    "/performance/dashboard",
    response_model=DemoPerformanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Measure dashboard performance",
    description="Runs the dashboard aggregation and checks the two-second demo budget.",
    openapi_extra={"x-roles": ["public"]},
)
async def measure_dashboard_performance(
    plant_id: str = Query(min_length=1, max_length=64, description="Plant identifier."),
    session: AsyncSession = Depends(get_db_session),
) -> DemoPerformanceResponse:
    """Return dashboard aggregation timing for demo-scale data."""
    return await DemoService.dashboard_performance(session, plant_id=plant_id)
