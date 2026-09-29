"""Incident model and incident evidence links for timeline reconstruction."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid
from app.models.enums import IncidentStatus, RiskLevel, enum_values


class Incident(TimestampMixin, Base):
    """Incident opened from one or more alerts and their supporting evidence."""

    __tablename__ = "incidents"
    __table_args__ = (
        Index("ix_incidents_plant_status_opened", "plant_id", "status", "opened_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    plant_id: Mapped[str] = mapped_column(
        ForeignKey("plants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    primary_alert_id: Mapped[str | None] = mapped_column(
        ForeignKey("alerts.id", ondelete="SET NULL"),
        nullable=True,
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
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(
            IncidentStatus,
            name="incident_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
        default=IncidentStatus.OPEN,
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    plant: Mapped["Plant"] = relationship()
    primary_alert: Mapped["Alert | None"] = relationship()
    evidence_links: Mapped[list["IncidentEvidenceLink"]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
    )


class IncidentEvidenceLink(TimestampMixin, Base):
    """Evidence record linking incidents to source events for forensic timelines."""

    __tablename__ = "incident_evidence_links"
    __table_args__ = (
        CheckConstraint(
            "alert_id IS NOT NULL "
            "OR sensor_reading_id IS NOT NULL "
            "OR permit_id IS NOT NULL "
            "OR maintenance_activity_id IS NOT NULL "
            "OR worker_location_event_id IS NOT NULL",
            name="ck_incident_evidence_has_source",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    incident_id: Mapped[str] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_id: Mapped[str | None] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=True,
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
    sequence_number: Mapped[int] = mapped_column(nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)

    incident: Mapped["Incident"] = relationship(back_populates="evidence_links")
    alert: Mapped["Alert | None"] = relationship()
    sensor_reading: Mapped["SensorReading | None"] = relationship()
    permit: Mapped["Permit | None"] = relationship()
    maintenance_activity: Mapped["MaintenanceActivity | None"] = relationship()
    worker_location_event: Mapped["WorkerLocationEvent | None"] = relationship()
