"""Shared SQLAlchemy declarative base and mixins for domain models."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


def new_uuid() -> str:
    """Return a string UUID suitable for portable primary keys."""
    return str(uuid4())


class TimestampMixin:
    """Add immutable creation and mutable update timestamps to a model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
