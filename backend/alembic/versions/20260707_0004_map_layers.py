"""Add plant map layout and hazard zone tables.

Revision ID: 20260707_0004
Revises: 20260707_0003
Create Date: 2026-07-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260707_0004"
down_revision: str | None = "20260707_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    """Return common timestamp columns."""
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    """Create map-layer tables."""
    op.create_table(
        "plant_layouts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("layout_type", sa.String(length=40), nullable=False),
        sa.Column("image_uri", sa.String(length=500), nullable=True),
        sa.Column("bounds", sa.JSON(), nullable=False),
        sa.Column("georeference", sa.JSON(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plant_layouts_plant_id", "plant_layouts", ["plant_id"])
    op.create_index("ix_plant_layouts_plant_active", "plant_layouts", ["plant_id", "is_active"])

    op.create_table(
        "hazard_zones",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=False),
        sa.Column("zone", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("hazard_type", sa.String(length=120), nullable=False),
        sa.Column("geometry", sa.JSON(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hazard_zones_plant_id", "hazard_zones", ["plant_id"])
    op.create_index("ix_hazard_zones_plant_zone", "hazard_zones", ["plant_id", "zone"])


def downgrade() -> None:
    """Drop map-layer tables."""
    op.drop_index("ix_hazard_zones_plant_zone", table_name="hazard_zones")
    op.drop_index("ix_hazard_zones_plant_id", table_name="hazard_zones")
    op.drop_table("hazard_zones")
    op.drop_index("ix_plant_layouts_plant_active", table_name="plant_layouts")
    op.drop_index("ix_plant_layouts_plant_id", table_name="plant_layouts")
    op.drop_table("plant_layouts")
