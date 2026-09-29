"""Sensor model for industrial telemetry sources."""

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid
from app.models.enums import SensorStatus, SensorType, enum_values


class Sensor(TimestampMixin, Base):
    """Configured sensor endpoint that produces time-series readings."""

    __tablename__ = "sensors"

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
    external_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    sensor_type: Mapped[SensorType] = mapped_column(
        Enum(
            SensorType,
            name="sensor_type",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    zone: Mapped[str] = mapped_column(String(120), nullable=False)
    x_coordinate: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    y_coordinate: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    status: Mapped[SensorStatus] = mapped_column(
        Enum(
            SensorStatus,
            name="sensor_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
        default=SensorStatus.ACTIVE,
    )

    plant: Mapped["Plant"] = relationship(back_populates="sensors")
    equipment: Mapped["Equipment | None"] = relationship(back_populates="sensors")
    readings: Mapped[list["SensorReading"]] = relationship(
        back_populates="sensor",
        cascade="all, delete-orphan",
    )
