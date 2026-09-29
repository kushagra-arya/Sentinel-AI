"""Permit model for event-driven work authorization."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid
from app.models.enums import PermitStatus, enum_values


class Permit(TimestampMixin, Base):
    """Safety permit such as hot work, confined-space, or isolation approval."""

    __tablename__ = "permits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    plant_id: Mapped[str] = mapped_column(
        ForeignKey("plants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    permit_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    permit_type: Mapped[str] = mapped_column(String(120), nullable=False)
    zone: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[PermitStatus] = mapped_column(
        Enum(
            PermitStatus,
            name="permit_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(Text)

    plant: Mapped["Plant"] = relationship()
    approved_by: Mapped["User | None"] = relationship()
