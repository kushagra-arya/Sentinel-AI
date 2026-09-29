"""Maintenance activity model for event-driven operational work."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid
from app.models.enums import MaintenanceStatus, enum_values


class MaintenanceActivity(TimestampMixin, Base):
    """Maintenance window that can combine with telemetry into compound risk."""

    __tablename__ = "maintenance_activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    plant_id: Mapped[str] = mapped_column(
        ForeignKey("plants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    equipment_id: Mapped[str | None] = mapped_column(
        ForeignKey("equipment.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    permit_id: Mapped[str | None] = mapped_column(
        ForeignKey("permits.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    work_order: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    maintenance_type: Mapped[str] = mapped_column(String(120), nullable=False)
    zone: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[MaintenanceStatus] = mapped_column(
        Enum(
            MaintenanceStatus,
            name="maintenance_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str | None] = mapped_column(Text)

    plant: Mapped["Plant"] = relationship()
    equipment: Mapped["Equipment | None"] = relationship(back_populates="maintenance_activities")
    permit: Mapped["Permit | None"] = relationship()
