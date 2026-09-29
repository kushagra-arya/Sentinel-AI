"""Notification API routes for dashboard and email delivery."""

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import require_roles
from app.models.enums import UserRole
from app.models.users import User
from app.schemas.notifications import (
    NotificationCreate,
    NotificationDispatchResponse,
    NotificationResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post(
    "",
    response_model=NotificationDispatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dispatch a notification",
    description=(
        "Sends a notification through dashboard and email channels, "
        "with future channel stubs."
    ),
    openapi_extra={"x-roles": ["admin", "safety_officer", "supervisor"]},
)
async def dispatch_notification(
    payload: NotificationCreate,
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.SAFETY_OFFICER, UserRole.SUPERVISOR)
    ),
    session: AsyncSession = Depends(get_db_session),
) -> NotificationDispatchResponse:
    """Dispatch a notification through the requested channels."""
    return await NotificationService.dispatch(
        session,
        payload=payload,
        actor_user_id=current_user.id,
    )


@router.get(
    "",
    response_model=list[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="List current-user notifications",
    description="Returns recent in-app notifications for the authenticated user.",
    openapi_extra={
        "x-roles": ["admin", "safety_officer", "supervisor", "compliance_officer", "viewer"]
    },
)
async def list_notifications(
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
) -> list[NotificationResponse]:
    """List dashboard notifications for the current user."""
    return await NotificationService.list_for_user(session, user_id=current_user.id)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark a notification as read",
    description="Marks one current-user notification as read and records an audit entry.",
    openapi_extra={
        "x-roles": ["admin", "safety_officer", "supervisor", "compliance_officer", "viewer"]
    },
)
async def mark_notification_read(
    notification_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$"),
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
) -> NotificationResponse:
    """Mark a current-user notification as read."""
    return await NotificationService.mark_read(
        session,
        notification_id=notification_id,
        user_id=current_user.id,
    )
