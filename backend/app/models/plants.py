"""Plant model for industrial sites monitored by SentinelAI."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid


class Plant(TimestampMixin, Base):
    """Industrial plant or facility boundary for all monitored entities."""

    __tablename__ = "plants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    description: Mapped[str | None] = mapped_column(Text)

    users: Mapped[list["User"]] = relationship(back_populates="plant")
    workers: Mapped[list["Worker"]] = relationship(back_populates="plant")
    sensors: Mapped[list["Sensor"]] = relationship(back_populates="plant")
    equipment: Mapped[list["Equipment"]] = relationship(back_populates="plant")
