"""Authentication token persistence for refresh-token revocation."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid


class RefreshToken(TimestampMixin, Base):
    """Refresh token identifier persisted for rotation and logout revocation."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_user_revoked_expires", "user_id", "revoked_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_jti: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_jti: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped["User"] = relationship()
