"""Worker and worker-location event models."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid


class Worker(TimestampMixin, Base):
    """Worker identity record used to correlate people with plant risk."""

    __tablename__ = "workers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    plant_id: Mapped[str] = mapped_column(
        ForeignKey("plants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    badge_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    plant: Mapped["Plant"] = relationship(back_populates="workers")
    location_events: Mapped[list["WorkerLocationEvent"]] = relationship(
        back_populates="worker",
        cascade="all, delete-orphan",
    )


class WorkerLocationEvent(TimestampMixin, Base):
    """Event-driven worker location update, not a high-frequency sensor stream."""

    __tablename__ = "worker_location_events"
    __table_args__ = (
        Index("ix_worker_location_worker_timestamp", "worker_id", "observed_at"),
        Index("ix_worker_location_plant_zone_timestamp", "plant_id", "zone", "observed_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    worker_id: Mapped[str] = mapped_column(
        ForeignKey("workers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plant_id: Mapped[str] = mapped_column(
        ForeignKey("plants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zone: Mapped[str] = mapped_column(String(120), nullable=False)
    x_coordinate: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    y_coordinate: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    worker: Mapped["Worker"] = relationship(back_populates="location_events")
    plant: Mapped["Plant"] = relationship()
