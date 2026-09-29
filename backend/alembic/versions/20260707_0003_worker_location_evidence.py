"""Add worker-location evidence links.

Revision ID: 20260707_0003
Revises: 20260707_0002
Create Date: 2026-07-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260707_0003"
down_revision: str | None = "20260707_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow alert and incident evidence to cite worker-location events."""
    op.add_column(
        "alert_evidence_links",
        sa.Column("worker_location_event_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_alert_evidence_links_worker_location_event_id",
        "alert_evidence_links",
        ["worker_location_event_id"],
    )
    op.create_foreign_key(
        "fk_alert_evidence_worker_location_event",
        "alert_evidence_links",
        "worker_location_events",
        ["worker_location_event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "ck_alert_evidence_has_source",
        "alert_evidence_links",
        type_="check",
    )
    op.create_check_constraint(
        "ck_alert_evidence_has_source",
        "alert_evidence_links",
        "sensor_reading_id IS NOT NULL "
        "OR permit_id IS NOT NULL "
        "OR maintenance_activity_id IS NOT NULL "
        "OR worker_location_event_id IS NOT NULL",
    )

    op.add_column(
        "incident_evidence_links",
        sa.Column("worker_location_event_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_incident_evidence_links_worker_location_event_id",
        "incident_evidence_links",
        ["worker_location_event_id"],
    )
    op.create_foreign_key(
        "fk_incident_evidence_worker_location_event",
        "incident_evidence_links",
        "worker_location_events",
        ["worker_location_event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "ck_incident_evidence_has_source",
        "incident_evidence_links",
        type_="check",
    )
    op.create_check_constraint(
        "ck_incident_evidence_has_source",
        "incident_evidence_links",
        "alert_id IS NOT NULL "
        "OR sensor_reading_id IS NOT NULL "
        "OR permit_id IS NOT NULL "
        "OR maintenance_activity_id IS NOT NULL "
        "OR worker_location_event_id IS NOT NULL",
    )


def downgrade() -> None:
    """Remove worker-location evidence links."""
    op.drop_constraint(
        "ck_incident_evidence_has_source",
        "incident_evidence_links",
        type_="check",
    )
    op.create_check_constraint(
        "ck_incident_evidence_has_source",
        "incident_evidence_links",
        "alert_id IS NOT NULL "
        "OR sensor_reading_id IS NOT NULL "
        "OR permit_id IS NOT NULL "
        "OR maintenance_activity_id IS NOT NULL",
    )
    op.drop_constraint(
        "fk_incident_evidence_worker_location_event",
        "incident_evidence_links",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_incident_evidence_links_worker_location_event_id",
        table_name="incident_evidence_links",
    )
    op.drop_column("incident_evidence_links", "worker_location_event_id")

    op.drop_constraint(
        "ck_alert_evidence_has_source",
        "alert_evidence_links",
        type_="check",
    )
    op.create_check_constraint(
        "ck_alert_evidence_has_source",
        "alert_evidence_links",
        "sensor_reading_id IS NOT NULL "
        "OR permit_id IS NOT NULL "
        "OR maintenance_activity_id IS NOT NULL",
    )
    op.drop_constraint(
        "fk_alert_evidence_worker_location_event",
        "alert_evidence_links",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_alert_evidence_links_worker_location_event_id",
        table_name="alert_evidence_links",
    )
    op.drop_column("alert_evidence_links", "worker_location_event_id")
