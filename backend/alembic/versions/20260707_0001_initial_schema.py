"""Create initial SentinelAI persistence schema.

Revision ID: 20260707_0001
Revises:
Create Date: 2026-07-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260707_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def enum_column(name: str, enum_name: str, values: list[str], nullable: bool = False) -> sa.Column:
    """Create a portable enum column with a database check constraint."""
    return sa.Column(
        name,
        sa.Enum(
            *values,
            name=enum_name,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=nullable,
    )


def timestamps() -> list[sa.Column]:
    """Return common creation and update timestamp columns."""
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    """Create all Phase 2 domain tables and supporting indexes."""
    op.create_table(
        "plants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        enum_column(
            "role",
            "user_role",
            ["admin", "safety_officer", "supervisor", "compliance_officer", "viewer"],
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_plant_id", "users", ["plant_id"])

    op.create_table(
        "workers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=False),
        sa.Column("badge_id", sa.String(length=64), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("role", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("badge_id"),
    )
    op.create_index("ix_workers_plant_id", "workers", ["plant_id"])

    op.create_table(
        "equipment",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=False),
        sa.Column("asset_tag", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("equipment_type", sa.String(length=120), nullable=False),
        sa.Column("zone", sa.String(length=120), nullable=False),
        enum_column(
            "status",
            "equipment_status",
            ["active", "maintenance", "offline", "decommissioned"],
        ),
        *timestamps(),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_tag"),
    )
    op.create_index("ix_equipment_plant_id", "equipment", ["plant_id"])

    op.create_table(
        "permits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=False),
        sa.Column("permit_number", sa.String(length=80), nullable=False),
        sa.Column("permit_type", sa.String(length=120), nullable=False),
        sa.Column("zone", sa.String(length=120), nullable=False),
        enum_column("status", "permit_status", ["requested", "active", "suspended", "closed", "expired"]),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("permit_number"),
    )
    op.create_index("ix_permits_plant_id", "permits", ["plant_id"])

    op.create_table(
        "worker_location_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("worker_id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=False),
        sa.Column("zone", sa.String(length=120), nullable=False),
        sa.Column("x_coordinate", sa.Numeric(10, 3), nullable=False),
        sa.Column("y_coordinate", sa.Numeric(10, 3), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_worker_location_events_plant_id", "worker_location_events", ["plant_id"])
    op.create_index("ix_worker_location_events_worker_id", "worker_location_events", ["worker_id"])
    op.create_index(
        "ix_worker_location_plant_zone_timestamp",
        "worker_location_events",
        ["plant_id", "zone", "observed_at"],
    )
    op.create_index(
        "ix_worker_location_worker_timestamp",
        "worker_location_events",
        ["worker_id", "observed_at"],
    )

    op.create_table(
        "maintenance_activities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=False),
        sa.Column("equipment_id", sa.String(length=36), nullable=True),
        sa.Column("permit_id", sa.String(length=36), nullable=True),
        sa.Column("work_order", sa.String(length=80), nullable=False),
        sa.Column("maintenance_type", sa.String(length=120), nullable=False),
        sa.Column("zone", sa.String(length=120), nullable=False),
        enum_column("status", "maintenance_status", ["planned", "active", "completed", "cancelled"]),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["permit_id"], ["permits.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_order"),
    )
    op.create_index("ix_maintenance_activities_equipment_id", "maintenance_activities", ["equipment_id"])
    op.create_index("ix_maintenance_activities_permit_id", "maintenance_activities", ["permit_id"])
    op.create_index("ix_maintenance_activities_plant_id", "maintenance_activities", ["plant_id"])

    op.create_table(
        "sensors",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=False),
        sa.Column("equipment_id", sa.String(length=36), nullable=True),
        sa.Column("external_id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        enum_column("sensor_type", "sensor_type", ["gas", "temperature", "pressure", "humidity", "ventilation"]),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("zone", sa.String(length=120), nullable=False),
        sa.Column("x_coordinate", sa.Numeric(10, 3), nullable=False),
        sa.Column("y_coordinate", sa.Numeric(10, 3), nullable=False),
        enum_column("status", "sensor_status", ["active", "maintenance", "offline"]),
        *timestamps(),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_sensors_equipment_id", "sensors", ["equipment_id"])
    op.create_index("ix_sensors_plant_id", "sensors", ["plant_id"])

    op.create_table(
        "sensor_readings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("sensor_id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Numeric(14, 4), nullable=False),
        sa.Column("quality", sa.String(length=32), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sensor_id"], ["sensors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sensor_readings_plant_id", "sensor_readings", ["plant_id"])
    op.create_index("ix_sensor_readings_sensor_id", "sensor_readings", ["sensor_id"])
    op.create_index("ix_sensor_readings_plant_measured_at", "sensor_readings", ["plant_id", "measured_at"])
    op.create_index("ix_sensor_readings_sensor_measured_at", "sensor_readings", ["sensor_id", "measured_at"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=False),
        enum_column("risk_level", "risk_level", ["low", "medium", "high", "critical"]),
        enum_column("status", "alert_status", ["open", "acknowledged", "resolved", "escalated"]),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["acknowledged_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_plant_id", "alerts", ["plant_id"])
    op.create_index("ix_alerts_plant_status_created", "alerts", ["plant_id", "status", "created_at"])

    op.create_table(
        "alert_evidence_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("alert_id", sa.String(length=36), nullable=False),
        sa.Column("sensor_reading_id", sa.String(length=36), nullable=True),
        sa.Column("permit_id", sa.String(length=36), nullable=True),
        sa.Column("maintenance_activity_id", sa.String(length=36), nullable=True),
        sa.Column("evidence_role", sa.String(length=80), nullable=False),
        *timestamps(),
        sa.CheckConstraint(
            "sensor_reading_id IS NOT NULL OR permit_id IS NOT NULL OR maintenance_activity_id IS NOT NULL",
            name="ck_alert_evidence_has_source",
        ),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["maintenance_activity_id"], ["maintenance_activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permit_id"], ["permits.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sensor_reading_id"], ["sensor_readings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_evidence_links_alert_id", "alert_evidence_links", ["alert_id"])
    op.create_index("ix_alert_evidence_links_maintenance_activity_id", "alert_evidence_links", ["maintenance_activity_id"])
    op.create_index("ix_alert_evidence_links_permit_id", "alert_evidence_links", ["permit_id"])
    op.create_index("ix_alert_evidence_links_sensor_reading_id", "alert_evidence_links", ["sensor_reading_id"])

    op.create_table(
        "incidents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=False),
        sa.Column("primary_alert_id", sa.String(length=36), nullable=True),
        enum_column("risk_level", "incident_risk_level", ["low", "medium", "high", "critical"]),
        enum_column("status", "incident_status", ["open", "investigating", "contained", "closed"]),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["primary_alert_id"], ["alerts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incidents_plant_id", "incidents", ["plant_id"])
    op.create_index("ix_incidents_primary_alert_id", "incidents", ["primary_alert_id"])
    op.create_index("ix_incidents_plant_status_opened", "incidents", ["plant_id", "status", "opened_at"])

    op.create_table(
        "incident_evidence_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("incident_id", sa.String(length=36), nullable=False),
        sa.Column("alert_id", sa.String(length=36), nullable=True),
        sa.Column("sensor_reading_id", sa.String(length=36), nullable=True),
        sa.Column("permit_id", sa.String(length=36), nullable=True),
        sa.Column("maintenance_activity_id", sa.String(length=36), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("evidence_role", sa.String(length=80), nullable=False),
        *timestamps(),
        sa.CheckConstraint(
            "alert_id IS NOT NULL OR sensor_reading_id IS NOT NULL OR permit_id IS NOT NULL OR maintenance_activity_id IS NOT NULL",
            name="ck_incident_evidence_has_source",
        ),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["maintenance_activity_id"], ["maintenance_activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permit_id"], ["permits.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sensor_reading_id"], ["sensor_readings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incident_evidence_links_alert_id", "incident_evidence_links", ["alert_id"])
    op.create_index("ix_incident_evidence_links_incident_id", "incident_evidence_links", ["incident_id"])
    op.create_index(
        "ix_incident_evidence_links_maintenance_activity_id",
        "incident_evidence_links",
        ["maintenance_activity_id"],
    )
    op.create_index("ix_incident_evidence_links_permit_id", "incident_evidence_links", ["permit_id"])
    op.create_index(
        "ix_incident_evidence_links_sensor_reading_id",
        "incident_evidence_links",
        ["sensor_reading_id"],
    )

    op.create_table(
        "risk_assessments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=False),
        sa.Column("alert_id", sa.String(length=36), nullable=True),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        enum_column("risk_level", "assessment_risk_level", ["low", "medium", "high", "critical"]),
        sa.Column("score", sa.Numeric(5, 4), nullable=False),
        sa.Column("rule_ids", sa.JSON(), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=True),
        sa.Column("model_version", sa.String(length=80), nullable=True),
        sa.Column("explanation", sa.JSON(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_assessments_alert", "risk_assessments", ["alert_id"])
    op.create_index("ix_risk_assessments_plant_id", "risk_assessments", ["plant_id"])
    op.create_index("ix_risk_assessments_plant_assessed_at", "risk_assessments", ["plant_id", "assessed_at"])

    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=220), nullable=False),
        enum_column(
            "document_type",
            "document_type",
            ["regulation", "sop", "incident_report", "maintenance_manual"],
        ),
        sa.Column("source_uri", sa.String(length=500), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("checksum"),
    )
    op.create_index("ix_documents_plant_id", "documents", ["plant_id"])
    op.create_index("ix_documents_plant_type", "documents", ["plant_id", "document_type"])

    op.create_table(
        "chat_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=True),
        sa.Column("conversation_id", sa.String(length=80), nullable=False),
        enum_column("role", "chat_role", ["user", "assistant", "system"]),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_history_conversation_id", "chat_history", ["conversation_id"])
    op.create_index("ix_chat_history_plant_id", "chat_history", ["plant_id"])
    op.create_index("ix_chat_history_user_id", "chat_history", ["user_id"])
    op.create_index("ix_chat_history_user_plant_created", "chat_history", ["user_id", "plant_id", "created_at"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("target_entity_type", sa.String(length=120), nullable=False),
        sa.Column("target_entity_id", sa.String(length=120), nullable=False),
        sa.Column("before_state", sa.JSON(), nullable=True),
        sa.Column("after_state", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_actor_timestamp", "audit_logs", ["actor_user_id", "timestamp"])
    op.create_index("ix_audit_logs_target", "audit_logs", ["target_entity_type", "target_entity_id"])


def downgrade() -> None:
    """Drop all Phase 2 schema objects in dependency order."""
    op.drop_index("ix_audit_logs_target", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_timestamp", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_chat_history_user_plant_created", table_name="chat_history")
    op.drop_index("ix_chat_history_user_id", table_name="chat_history")
    op.drop_index("ix_chat_history_plant_id", table_name="chat_history")
    op.drop_index("ix_chat_history_conversation_id", table_name="chat_history")
    op.drop_table("chat_history")
    op.drop_index("ix_documents_plant_type", table_name="documents")
    op.drop_index("ix_documents_plant_id", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_risk_assessments_plant_assessed_at", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_plant_id", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_alert", table_name="risk_assessments")
    op.drop_table("risk_assessments")
    op.drop_index("ix_incident_evidence_links_sensor_reading_id", table_name="incident_evidence_links")
    op.drop_index("ix_incident_evidence_links_permit_id", table_name="incident_evidence_links")
    op.drop_index("ix_incident_evidence_links_maintenance_activity_id", table_name="incident_evidence_links")
    op.drop_index("ix_incident_evidence_links_incident_id", table_name="incident_evidence_links")
    op.drop_index("ix_incident_evidence_links_alert_id", table_name="incident_evidence_links")
    op.drop_table("incident_evidence_links")
    op.drop_index("ix_incidents_plant_status_opened", table_name="incidents")
    op.drop_index("ix_incidents_primary_alert_id", table_name="incidents")
    op.drop_index("ix_incidents_plant_id", table_name="incidents")
    op.drop_table("incidents")
    op.drop_index("ix_alert_evidence_links_sensor_reading_id", table_name="alert_evidence_links")
    op.drop_index("ix_alert_evidence_links_permit_id", table_name="alert_evidence_links")
    op.drop_index("ix_alert_evidence_links_maintenance_activity_id", table_name="alert_evidence_links")
    op.drop_index("ix_alert_evidence_links_alert_id", table_name="alert_evidence_links")
    op.drop_table("alert_evidence_links")
    op.drop_index("ix_alerts_plant_status_created", table_name="alerts")
    op.drop_index("ix_alerts_plant_id", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_sensor_readings_sensor_measured_at", table_name="sensor_readings")
    op.drop_index("ix_sensor_readings_plant_measured_at", table_name="sensor_readings")
    op.drop_index("ix_sensor_readings_sensor_id", table_name="sensor_readings")
    op.drop_index("ix_sensor_readings_plant_id", table_name="sensor_readings")
    op.drop_table("sensor_readings")
    op.drop_index("ix_sensors_plant_id", table_name="sensors")
    op.drop_index("ix_sensors_equipment_id", table_name="sensors")
    op.drop_table("sensors")
    op.drop_index("ix_maintenance_activities_plant_id", table_name="maintenance_activities")
    op.drop_index("ix_maintenance_activities_permit_id", table_name="maintenance_activities")
    op.drop_index("ix_maintenance_activities_equipment_id", table_name="maintenance_activities")
    op.drop_table("maintenance_activities")
    op.drop_index("ix_worker_location_worker_timestamp", table_name="worker_location_events")
    op.drop_index("ix_worker_location_plant_zone_timestamp", table_name="worker_location_events")
    op.drop_index("ix_worker_location_events_worker_id", table_name="worker_location_events")
    op.drop_index("ix_worker_location_events_plant_id", table_name="worker_location_events")
    op.drop_table("worker_location_events")
    op.drop_index("ix_permits_plant_id", table_name="permits")
    op.drop_table("permits")
    op.drop_index("ix_equipment_plant_id", table_name="equipment")
    op.drop_table("equipment")
    op.drop_index("ix_workers_plant_id", table_name="workers")
    op.drop_table("workers")
    op.drop_index("ix_users_plant_id", table_name="users")
    op.drop_table("users")
    op.drop_table("plants")
