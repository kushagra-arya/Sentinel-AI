"""Schemas for emergency response and incident report generation."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import RiskLevel
from app.schemas.timeline import TimelineEntry


class WorkerPresence(BaseModel):
    """Worker present in an affected area."""

    worker_id: str = Field(description="Worker identifier.")
    badge_id: str | None = Field(description="Worker badge when available.")
    full_name: str | None = Field(description="Worker name when available.")
    zone: str = Field(description="Observed zone.")
    observed_at: datetime = Field(description="Observation time.")


class NearbyEquipment(BaseModel):
    """Equipment near or in an affected area."""

    equipment_id: str = Field(description="Equipment identifier.")
    asset_tag: str = Field(description="Equipment asset tag.")
    name: str = Field(description="Equipment name.")
    equipment_type: str = Field(description="Equipment type.")
    zone: str = Field(description="Equipment zone.")
    status: str = Field(description="Equipment status.")


class EmergencyContact(BaseModel):
    """Emergency contact shown during live response."""

    role: str = Field(description="Response role.")
    name: str = Field(description="Contact name.")
    channel: str = Field(description="Primary contact channel.")


class RoleAction(BaseModel):
    """Concrete role-specific action item."""

    role: str = Field(description="Responsible role.")
    action: str = Field(description="Action to perform.")
    priority: int = Field(description="Action priority, lower is earlier.")


class EvidenceSummaryItem(BaseModel):
    """Audit-ready evidence summary item."""

    entity_type: str = Field(description="Evidence entity type.")
    entity_id: str = Field(description="Evidence identifier.")
    observed_at: datetime | None = Field(description="Evidence timestamp.")
    description: str = Field(description="Evidence description.")
    value: str | None = Field(description="Evidence value if applicable.")


class EmergencyPanelState(BaseModel):
    """Live emergency panel state computed from incident evidence."""

    incident_id: str = Field(description="Incident identifier.")
    affected_area: str = Field(description="Affected zone or area.")
    risk_level: RiskLevel = Field(description="Incident risk level.")
    triggering_rules: list[str] = Field(description="Rules inferred from linked alert sources.")
    workers_present: list[WorkerPresence] = Field(description="Workers present in affected area.")
    nearby_equipment: list[NearbyEquipment] = Field(
        description="Nearby equipment in affected area."
    )
    nearest_exit: str = Field(description="Nearest exit based on affected area.")
    emergency_contacts: list[EmergencyContact] = Field(description="Emergency contacts.")
    recommended_actions: list[RoleAction] = Field(description="Role-specific response actions.")


class IncidentReport(BaseModel):
    """Generated incident report that drives screen and export output."""

    incident_id: str = Field(description="Incident identifier.")
    generated_at: datetime = Field(description="Report generation timestamp.")
    risk_type: str = Field(description="Risk type inferred from triggering rules.")
    affected_zone: str = Field(description="Affected zone.")
    triggering_rules: list[str] = Field(description="Triggering rule identifiers.")
    panel: EmergencyPanelState = Field(description="Emergency response panel state.")
    timeline: list[TimelineEntry] = Field(description="Generated incident timeline.")
    action_checklist: list[RoleAction] = Field(description="Role-specific action checklist.")
    evidence_summary: list[EvidenceSummaryItem] = Field(description="Audit-ready evidence summary.")


class ExportResponse(BaseModel):
    """File export response payload."""

    filename: str = Field(description="Export filename.")
    media_type: str = Field(description="Export media type.")
    content_base64: str = Field(description="Base64-encoded export content.")


class ReportStubResponse(BaseModel):
    """Stub response for report types that share the export pipeline later."""

    report_type: str = Field(description="Requested report type.")
    status: str = Field(description="Current implementation status.")
    export_pipeline: str = Field(description="Pipeline that will be reused.")
