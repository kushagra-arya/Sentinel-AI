"""Notification persistence for in-app dashboard delivery."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid


class Notification(TimestampMixin, Base):
    """Dashboard notification delivered to a specific user."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_read_created", "user_id", "read_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plant_id: Mapped[str | None] = mapped_column(
        ForeignKey("plants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="informational")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship()
    plant: Mapped["Plant | None"] = relationship()
