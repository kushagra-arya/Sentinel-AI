"""Audit log model for mutating actions and security-relevant events."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, new_uuid


class AuditLog(Base):
    """Immutable audit entry capturing actor, action, target, and state diff."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_actor_timestamp", "actor_user_id", "timestamp"),
        Index("ix_audit_logs_target", "target_entity_type", "target_entity_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    actor_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    target_entity_type: Mapped[str] = mapped_column(String(120), nullable=False)
    target_entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    before_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    actor: Mapped["User | None"] = relationship(back_populates="audit_logs")
