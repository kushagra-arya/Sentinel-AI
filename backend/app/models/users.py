"""User model for operators and safety stakeholders."""

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid
from app.models.enums import UserRole, enum_values


class User(TimestampMixin, Base):
    """Authenticated SentinelAI user with an auditable role assignment."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    plant_id: Mapped[str | None] = mapped_column(
        ForeignKey("plants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    plant: Mapped["Plant | None"] = relationship(back_populates="users")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="actor")
