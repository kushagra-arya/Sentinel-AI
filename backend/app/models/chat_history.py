"""Chat history model for persisted AI assistant conversations."""

from sqlalchemy import Enum, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid
from app.models.enums import ChatRole, enum_values


class ChatHistory(TimestampMixin, Base):
    """Single chat turn with citation metadata for auditability."""

    __tablename__ = "chat_history"
    __table_args__ = (
        Index("ix_chat_history_user_plant_created", "user_id", "plant_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plant_id: Mapped[str | None] = mapped_column(
        ForeignKey("plants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    conversation_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    role: Mapped[ChatRole] = mapped_column(
        Enum(
            ChatRole,
            name="chat_role",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)

    user: Mapped["User"] = relationship()
    plant: Mapped["Plant | None"] = relationship()
