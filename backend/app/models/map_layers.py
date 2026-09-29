"""Plant map layout and hazard-zone persistence models."""

from sqlalchemy import ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid


class PlantLayout(TimestampMixin, Base):
    """Uploaded or coordinate-defined plant layout used by map clients."""

    __tablename__ = "plant_layouts"
    __table_args__ = (Index("ix_plant_layouts_plant_active", "plant_id", "is_active"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    plant_id: Mapped[str] = mapped_column(
        ForeignKey("plants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    layout_type: Mapped[str] = mapped_column(String(40), nullable=False)
    image_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bounds: Mapped[dict] = mapped_column(JSON, nullable=False)
    georeference: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    plant: Mapped["Plant"] = relationship()


class HazardZone(TimestampMixin, Base):
    """Named plant hazard zone represented as a polygon or bounding geometry."""

    __tablename__ = "hazard_zones"
    __table_args__ = (Index("ix_hazard_zones_plant_zone", "plant_id", "zone"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    plant_id: Mapped[str] = mapped_column(
        ForeignKey("plants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zone: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    hazard_type: Mapped[str] = mapped_column(String(120), nullable=False)
    geometry: Mapped[dict] = mapped_column(JSON, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)

    plant: Mapped["Plant"] = relationship()
