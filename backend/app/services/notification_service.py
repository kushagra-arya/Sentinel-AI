"""Notification dispatch service and channel implementations."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.notifications import Notification
from app.schemas.notifications import (
    NotificationCreate,
    NotificationDelivery,
    NotificationDispatchResponse,
    NotificationResponse,
)
from app.services.audit_service import AuditService

logger = get_logger(__name__)


class NotificationChannel(ABC):
    """Common interface for notification delivery channels."""

    name: str

    @abstractmethod
    async def deliver(
        self,
        session: AsyncSession,
        payload: NotificationCreate,
    ) -> tuple[Notification | None, NotificationDelivery]:
        """Deliver a notification payload through the channel."""


class DashboardNotificationChannel(NotificationChannel):
    """Persist in-app dashboard notifications."""

    name = "dashboard"

    async def deliver(
        self,
        session: AsyncSession,
        payload: NotificationCreate,
    ) -> tuple[Notification | None, NotificationDelivery]:
        """Persist the notification for dashboard retrieval."""
        notification = Notification(
            user_id=payload.user_id,
            plant_id=payload.plant_id,
            title=payload.title,
            body=payload.body,
            severity=payload.severity,
        )
        session.add(notification)
        await session.flush()
        return notification, NotificationDelivery(
            channel=self.name,
            status="delivered",
            detail="Stored for in-app dashboard delivery.",
        )


class EmailNotificationChannel(NotificationChannel):
    """Email notification channel represented by auditable queued delivery."""

    name = "email"

    async def deliver(
        self,
        session: AsyncSession,
        payload: NotificationCreate,
    ) -> tuple[Notification | None, NotificationDelivery]:
        """Queue an email notification as an auditable delivery event."""
        logger.info(
            "email_notification_queued",
            extra={"recipient_user_id": payload.user_id, "title": payload.title},
        )
        await AuditService.record(
            session,
            actor_user_id=None,
            action="email_notification_queued",
            target_entity_type="user",
            target_entity_id=payload.user_id,
            after_state={"title": payload.title, "severity": payload.severity},
        )
        return None, NotificationDelivery(
            channel=self.name,
            status="queued",
            detail="Email delivery queued and audit logged.",
        )


class FutureNotificationChannel(NotificationChannel):
    """Stub channel for future SMS, Teams, and Slack integrations."""

    def __init__(self, name: str) -> None:
        """Create a future channel by name."""
        self.name = name

    async def deliver(
        self,
        session: AsyncSession,
        payload: NotificationCreate,
    ) -> tuple[Notification | None, NotificationDelivery]:
        """Return a clear not-configured response without side effects."""
        return None, NotificationDelivery(
            channel=self.name,
            status="not_configured",
            detail=f"{self.name} delivery is reserved for a future integration.",
        )


class NotificationService:
    """Dispatch and retrieve notifications through configured channels."""

    channels: dict[str, NotificationChannel] = {
        "dashboard": DashboardNotificationChannel(),
        "email": EmailNotificationChannel(),
        "sms": FutureNotificationChannel("sms"),
        "teams": FutureNotificationChannel("teams"),
        "slack": FutureNotificationChannel("slack"),
    }

    @staticmethod
    async def dispatch(
        session: AsyncSession,
        *,
        payload: NotificationCreate,
        actor_user_id: str,
    ) -> NotificationDispatchResponse:
        """Deliver a notification request through one or more channels."""
        deliveries: list[NotificationDelivery] = []
        dashboard_record: Notification | None = None
        for channel_name in payload.channels:
            channel = NotificationService.channels.get(channel_name)
            if channel is None:
                deliveries.append(
                    NotificationDelivery(
                        channel=channel_name,
                        status="rejected",
                        detail="Unknown notification channel.",
                    )
                )
                continue
            record, delivery = await channel.deliver(session, payload)
            deliveries.append(delivery)
            dashboard_record = record or dashboard_record

        await AuditService.record(
            session,
            actor_user_id=actor_user_id,
            action="notification_dispatch",
            target_entity_type="user",
            target_entity_id=payload.user_id,
            after_state={"channels": payload.channels, "title": payload.title},
        )
        await session.commit()
        if dashboard_record is not None:
            await session.refresh(dashboard_record)

        return NotificationDispatchResponse(
            notification=NotificationService._to_response(dashboard_record)
            if dashboard_record is not None
            else None,
            deliveries=deliveries,
        )

    @staticmethod
    async def list_for_user(session: AsyncSession, *, user_id: str) -> list[NotificationResponse]:
        """Return recent dashboard notifications for a user."""
        result = await session.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(desc(Notification.created_at))
            .limit(50)
        )
        return [NotificationService._to_response(notification) for notification in result.scalars()]

    @staticmethod
    async def mark_read(
        session: AsyncSession,
        *,
        notification_id: str,
        user_id: str,
    ) -> NotificationResponse:
        """Mark a user's notification as read."""
        notification = await session.get(Notification, notification_id)
        if notification is None or notification.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found.",
            )

        before_state = {
            "read_at": notification.read_at.isoformat() if notification.read_at else None
        }
        notification.read_at = datetime.now(UTC)
        await AuditService.record(
            session,
            actor_user_id=user_id,
            action="notification_mark_read",
            target_entity_type="notification",
            target_entity_id=notification.id,
            before_state=before_state,
            after_state={"read_at": notification.read_at.isoformat()},
        )
        await session.commit()
        await session.refresh(notification)
        return NotificationService._to_response(notification)

    @staticmethod
    def _to_response(notification: Notification | None) -> NotificationResponse | None:
        """Map a notification ORM object to its API schema."""
        if notification is None:
            return None
        return NotificationResponse(
            id=notification.id,
            user_id=notification.user_id,
            plant_id=notification.plant_id,
            title=notification.title,
            body=notification.body,
            severity=notification.severity,
            read_at=notification.read_at,
            created_at=notification.created_at,
        )
