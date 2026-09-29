"""Enumerations used by SentinelAI persistence models."""

from enum import StrEnum


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    """Return persisted enum values for SQLAlchemy Enum columns."""
    return [member.value for member in enum_cls]


class UserRole(StrEnum):
    """Supported application roles for access control."""

    ADMIN = "admin"
    SAFETY_OFFICER = "safety_officer"
    SUPERVISOR = "supervisor"
    COMPLIANCE_OFFICER = "compliance_officer"
    VIEWER = "viewer"


class RiskLevel(StrEnum):
    """Auditable risk levels used by assessments, alerts, and incidents."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SensorType(StrEnum):
    """Supported industrial sensor categories."""

    GAS = "gas"
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    HUMIDITY = "humidity"
    VENTILATION = "ventilation"


class SensorStatus(StrEnum):
    """Operational state of a sensor."""

    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"


class EquipmentStatus(StrEnum):
    """Operational state of plant equipment."""

    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"
    DECOMMISSIONED = "decommissioned"


class PermitStatus(StrEnum):
    """Lifecycle states for safety permits."""

    REQUESTED = "requested"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    EXPIRED = "expired"


class AlertStatus(StrEnum):
    """Lifecycle states for safety alerts."""

    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class IncidentStatus(StrEnum):
    """Lifecycle states for incidents."""

    OPEN = "open"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    CLOSED = "closed"


class MaintenanceStatus(StrEnum):
    """Lifecycle states for maintenance activity."""

    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DocumentType(StrEnum):
    """Document corpus categories used by the safety assistant."""

    REGULATION = "regulation"
    SOP = "sop"
    INCIDENT_REPORT = "incident_report"
    MAINTENANCE_MANUAL = "maintenance_manual"


class ChatRole(StrEnum):
    """Speaker roles for persisted assistant conversations."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
