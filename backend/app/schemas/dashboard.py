"""Pydantic schemas for dashboard aggregation responses."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import RiskLevel


class StatusSummary(BaseModel):
    """Status summary for a dashboard metric group."""

    status: str = Field(description="Human-readable status.")
    value: float | int | None = Field(description="Latest metric value.")
    unit: str | None = Field(description="Metric unit.")
    observed_at: datetime | None = Field(description="Timestamp for the latest value.")


class DashboardEvent(BaseModel):
    """Single event item shown in the live dashboard feed."""

    event_type: str = Field(description="Event source type.")
    title: str = Field(description="Event title.")
    severity: str = Field(description="Event severity or risk level.")
    occurred_at: datetime = Field(description="Event timestamp.")


class DashboardSummary(BaseModel):
    """Single-call command-center dashboard aggregation."""

    plant_id: str = Field(description="Plant identifier for the aggregation.")
    current_risk_score: float = Field(description="Latest plant risk score.")
    current_risk_level: RiskLevel = Field(description="Latest plant risk level.")
    active_alerts: int = Field(description="Number of open or acknowledged alerts.")
    critical_alerts: int = Field(description="Number of active critical alerts.")
    worker_count: int = Field(description="Active workers assigned to the plant.")
    active_permits: int = Field(description="Currently active permits.")
    maintenance_activities: int = Field(description="Active maintenance work windows.")
    gas_status: StatusSummary = Field(description="Latest gas telemetry status.")
    temperature_status: StatusSummary = Field(description="Latest temperature telemetry status.")
    equipment_health: StatusSummary = Field(description="Equipment health summary.")
    recent_incidents: int = Field(description="Recently opened incidents.")
    live_event_feed: list[DashboardEvent] = Field(description="Recent operational events.")
