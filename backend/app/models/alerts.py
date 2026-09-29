"""Alert model and alert evidence links for explainability."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid
from app.models.enums import AlertStatus, RiskLevel, enum_values


class Alert(TimestampMixin, Base):
    """Safety alert raised by rules, models, or operator workflow."""

    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alerts_plant_status_created", "plant_id", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    plant_id: Mapped[str] = mapped_column(
        ForeignKey("plants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(
            RiskLevel,
            name="risk_level",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    status: Mapped[AlertStatus] = mapped_column(
        Enum(
            AlertStatus,
            name="alert_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
        default=AlertStatus.OPEN,
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    plant: Mapped["Plant"] = relationship()
    acknowledged_by: Mapped["User | None"] = relationship()
    evidence_links: Mapped[list["AlertEvidenceLink"]] = relationship(
        back_populates="alert",
        cascade="all, delete-orphan",
    )


class AlertEvidenceLink(TimestampMixin, Base):
    """Evidence record linking an alert to the exact records that caused it."""

    __tablename__ = "alert_evidence_links"
    __table_args__ = (
        CheckConstraint(
            "sensor_reading_id IS NOT NULL "
            "OR permit_id IS NOT NULL "
            "OR maintenance_activity_id IS NOT NULL "
            "OR worker_location_event_id IS NOT NULL",
            name="ck_alert_evidence_has_source",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    alert_id: Mapped[str] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sensor_reading_id: Mapped[str | None] = mapped_column(
        ForeignKey("sensor_readings.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    permit_id: Mapped[str | None] = mapped_column(
        ForeignKey("permits.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    maintenance_activity_id: Mapped[str | None] = mapped_column(
        ForeignKey("maintenance_activities.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    worker_location_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("worker_location_events.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)

    alert: Mapped["Alert"] = relationship(back_populates="evidence_links")
    sensor_reading: Mapped["SensorReading | None"] = relationship()
    permit: Mapped["Permit | None"] = relationship()
    maintenance_activity: Mapped["MaintenanceActivity | None"] = relationship()
    worker_location_event: Mapped["WorkerLocationEvent | None"] = relationship()
