"""Equipment model for plant assets monitored by SentinelAI."""

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid
from app.models.enums import EquipmentStatus, enum_values


class Equipment(TimestampMixin, Base):
    """Industrial asset that can be associated with sensors and maintenance."""

    __tablename__ = "equipment"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    plant_id: Mapped[str] = mapped_column(
        ForeignKey("plants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_tag: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    equipment_type: Mapped[str] = mapped_column(String(120), nullable=False)
    zone: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[EquipmentStatus] = mapped_column(
        Enum(
            EquipmentStatus,
            name="equipment_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
        default=EquipmentStatus.ACTIVE,
    )

    plant: Mapped["Plant"] = relationship(back_populates="equipment")
    sensors: Mapped[list["Sensor"]] = relationship(back_populates="equipment")
    maintenance_activities: Mapped[list["MaintenanceActivity"]] = relationship(
        back_populates="equipment"
    )
