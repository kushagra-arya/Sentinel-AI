"""Add auth refresh tokens and dashboard notifications.

Revision ID: 20260707_0002
Revises: 20260707_0001
Create Date: 2026-07-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260707_0002"
down_revision: str | None = "20260707_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    """Return common creation and update timestamp columns."""
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    """Create auth-token and notification service tables."""
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_jti", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_jti", sa.String(length=64), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_jti"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index(
        "ix_refresh_tokens_user_revoked_expires",
        "refresh_tokens",
        ["user_id", "revoked_at", "expires_at"],
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_plant_id", "notifications", ["plant_id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index(
        "ix_notifications_user_read_created",
        "notifications",
        ["user_id", "read_at", "created_at"],
    )


def downgrade() -> None:
    """Drop auth-token and notification service tables."""
    op.drop_index("ix_notifications_user_read_created", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_index("ix_notifications_plant_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_refresh_tokens_user_revoked_expires", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
