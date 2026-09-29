"""Pydantic schemas for notification endpoints."""

from datetime import datetime

from typing import Literal

from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    """Request to dispatch a notification through configured channels."""

    user_id: str = Field(min_length=1, max_length=64, description="Recipient user identifier.")
    plant_id: str | None = Field(
        default=None,
        max_length=64,
        description="Related plant identifier.",
    )
    title: str = Field(min_length=1, max_length=180, description="Notification title.")
    body: str = Field(min_length=1, max_length=4000, description="Notification body.")
    severity: Literal["informational", "low", "medium", "high", "critical"] = Field(
        default="informational",
        description="Operational severity label.",
    )
    channels: list[Literal["dashboard", "email", "sms", "teams", "slack"]] = Field(
        default_factory=lambda: ["dashboard"],
        min_length=1,
        max_length=5,
        description="Delivery channels: dashboard, email, sms, teams, or slack.",
    )


class NotificationDelivery(BaseModel):
    """Delivery result for a single notification channel."""

    channel: str = Field(description="Delivery channel name.")
    status: str = Field(description="Delivery status.")
    detail: str = Field(description="Human-readable delivery detail.")


class NotificationResponse(BaseModel):
    """Persisted notification returned to API clients."""

    id: str = Field(description="Notification identifier.")
    user_id: str = Field(description="Recipient user identifier.")
    plant_id: str | None = Field(description="Related plant identifier.")
    title: str = Field(description="Notification title.")
    body: str = Field(description="Notification body.")
    severity: str = Field(description="Operational severity label.")
    read_at: datetime | None = Field(description="Timestamp when the notification was read.")
    created_at: datetime = Field(description="Creation timestamp.")


class NotificationDispatchResponse(BaseModel):
    """Response containing channel delivery results."""

    notification: NotificationResponse | None = Field(
        description="Dashboard notification record when dashboard delivery was requested."
    )
    deliveries: list[NotificationDelivery] = Field(description="Per-channel delivery results.")
