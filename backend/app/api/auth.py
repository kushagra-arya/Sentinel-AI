"""Authentication API routes for SentinelAI."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.rate_limit import rate_limit
from app.core.security import get_current_user
from app.models.users import User
from app.schemas.auth import (
    AuthenticatedSession,
    LoginRequest,
    LogoutRequest,
    LogoutResponse,
    RefreshRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=AuthenticatedSession,
    status_code=status.HTTP_200_OK,
    summary="Authenticate a user",
    description="Verifies credentials and issues JWT access and refresh tokens.",
    openapi_extra={"x-roles": ["public"]},
)
async def login(
    payload: LoginRequest,
    _rate_limited: None = Depends(rate_limit("auth")),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedSession:
    """Exchange valid user credentials for access and refresh tokens."""
    return await AuthService.login(
        session,
        email=payload.email,
        password=payload.password,
        settings=settings,
    )


@router.post(
    "/refresh",
    response_model=AuthenticatedSession,
    status_code=status.HTTP_200_OK,
    summary="Refresh an authenticated session",
    description="Rotates a valid refresh token and returns a new JWT token pair.",
    openapi_extra={"x-roles": ["public"]},
)
async def refresh(
    payload: RefreshRequest,
    _rate_limited: None = Depends(rate_limit("auth")),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedSession:
    """Rotate a refresh token and return a fresh authenticated session."""
    return await AuthService.refresh(
        session,
        refresh_token=payload.refresh_token,
        settings=settings,
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout an authenticated user",
    description="Revokes the supplied refresh token for the authenticated user.",
    openapi_extra={"x-roles": ["authenticated"]},
)
async def logout(
    payload: LogoutRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> LogoutResponse:
    """Revoke a refresh token for the current authenticated user."""
    await AuthService.logout(
        session,
        refresh_token=payload.refresh_token,
        settings=settings,
        actor_user_id=current_user.id,
    )
    return LogoutResponse(status="logged_out")
