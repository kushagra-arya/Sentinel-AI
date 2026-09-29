"""High-volume sensor reading model.

Sensor readings are modeled as append-only time-series rows with a composite
index on `(sensor_id, measured_at)` for the dominant "sensor over time window"
query and an additional plant/time index for dashboard windows. For Phase 2 we
use a regular PostgreSQL table plus documented indexes instead of declarative
range partitions: demo scale and Alembic portability matter now, while later
high-retention deployments can migrate this table to monthly range partitions
or TimescaleDB hypertables without changing ORM consumers.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid


class SensorReading(TimestampMixin, Base):
    """Append-only measurement emitted by a configured industrial sensor."""

    __tablename__ = "sensor_readings"
    __table_args__ = (
        Index("ix_sensor_readings_sensor_measured_at", "sensor_id", "measured_at"),
        Index("ix_sensor_readings_plant_measured_at", "plant_id", "measured_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    sensor_id: Mapped[str] = mapped_column(
        ForeignKey("sensors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plant_id: Mapped[str] = mapped_column(
        ForeignKey("plants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    quality: Mapped[str] = mapped_column(String(32), nullable=False, default="good")

    sensor: Mapped["Sensor"] = relationship(back_populates="readings")
    plant: Mapped["Plant"] = relationship()
