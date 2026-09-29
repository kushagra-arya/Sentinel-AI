"""Risk assessment model with rule and model auditability."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid
from app.models.enums import RiskLevel, enum_values


class RiskAssessment(TimestampMixin, Base):
    """Persisted risk score with traceable rule and model provenance."""

    __tablename__ = "risk_assessments"
    __table_args__ = (
        Index("ix_risk_assessments_plant_assessed_at", "plant_id", "assessed_at"),
        Index("ix_risk_assessments_alert", "alert_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    plant_id: Mapped[str] = mapped_column(
        ForeignKey("plants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_id: Mapped[str | None] = mapped_column(
        ForeignKey("alerts.id", ondelete="SET NULL"),
        nullable=True,
    )
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
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
    score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    rule_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    explanation: Mapped[dict] = mapped_column(JSON, nullable=False)

    plant: Mapped["Plant"] = relationship()
    alert: Mapped["Alert | None"] = relationship()
