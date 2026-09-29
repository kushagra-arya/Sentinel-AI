"""Dashboard aggregation service for command-center summaries."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerts import Alert
from app.models.enums import (
    AlertStatus,
    EquipmentStatus,
    IncidentStatus,
    MaintenanceStatus,
    PermitStatus,
    RiskLevel,
    SensorType,
)
from app.models.equipment import Equipment
from app.models.incidents import Incident
from app.models.maintenance import MaintenanceActivity
from app.models.notifications import Notification
from app.models.permits import Permit
from app.models.risk_assessments import RiskAssessment
from app.models.sensor_readings import SensorReading
from app.models.sensors import Sensor
from app.models.workers import Worker
from app.schemas.dashboard import DashboardEvent, DashboardSummary, StatusSummary


class DashboardService:
    """Build a single dashboard payload from indexed aggregate queries.

    Query strategy: keep the route to one service call, use narrow indexed
    count/latest queries on `plant_id`, status, and timestamp columns, and cap
    live-feed collections. At demo scale this avoids ORM relationship loading
    and holds the dashboard under the two-second budget without requiring an
    external cache. Later phases can put this method behind a short TTL cache
    without changing the API contract.
    """

    @staticmethod
    async def get_summary(session: AsyncSession, *, plant_id: str) -> DashboardSummary:
        """Return the current plant dashboard aggregation."""
        now = datetime.now(UTC)
        latest_risk = await DashboardService._latest_risk(session, plant_id)
        active_alerts = await DashboardService._count_active_alerts(session, plant_id)
        critical_alerts = await DashboardService._count_critical_alerts(session, plant_id)
        worker_count = await DashboardService._count_workers(session, plant_id)
        active_permits = await DashboardService._count_active_permits(session, plant_id, now)
        maintenance = await DashboardService._count_active_maintenance(session, plant_id)
        gas_status = await DashboardService._latest_sensor_status(session, plant_id, SensorType.GAS)
        temperature_status = await DashboardService._latest_sensor_status(
            session,
            plant_id,
            SensorType.TEMPERATURE,
        )
        equipment_health = await DashboardService._equipment_health(session, plant_id)
        recent_incidents = await DashboardService._count_recent_incidents(session, plant_id, now)
        live_event_feed = await DashboardService._live_event_feed(session, plant_id)

        return DashboardSummary(
            plant_id=plant_id,
            current_risk_score=latest_risk.score,
            current_risk_level=latest_risk.level,
            active_alerts=active_alerts,
            critical_alerts=critical_alerts,
            worker_count=worker_count,
            active_permits=active_permits,
            maintenance_activities=maintenance,
            gas_status=gas_status,
            temperature_status=temperature_status,
            equipment_health=equipment_health,
            recent_incidents=recent_incidents,
            live_event_feed=live_event_feed,
        )

    @staticmethod
    async def _latest_risk(session: AsyncSession, plant_id: str) -> "_RiskSnapshot":
        """Return latest risk assessment or a safe default when none exists."""
        result = await session.execute(
            select(RiskAssessment)
            .where(RiskAssessment.plant_id == plant_id)
            .order_by(desc(RiskAssessment.assessed_at))
            .limit(1)
        )
        assessment = result.scalar_one_or_none()
        if assessment is None:
            return _RiskSnapshot(score=0.0, level=RiskLevel.LOW)
        return _RiskSnapshot(score=float(assessment.score), level=assessment.risk_level)

    @staticmethod
    async def _count_active_alerts(session: AsyncSession, plant_id: str) -> int:
        """Count alerts that still require operator awareness."""
        result = await session.execute(
            select(func.count(Alert.id)).where(
                Alert.plant_id == plant_id,
                Alert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]),
            )
        )
        return int(result.scalar_one())

    @staticmethod
    async def _count_critical_alerts(session: AsyncSession, plant_id: str) -> int:
        """Count critical active alerts."""
        result = await session.execute(
            select(func.count(Alert.id)).where(
                Alert.plant_id == plant_id,
                Alert.risk_level == RiskLevel.CRITICAL,
                Alert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]),
            )
        )
        return int(result.scalar_one())

    @staticmethod
    async def _count_workers(session: AsyncSession, plant_id: str) -> int:
        """Count active workers assigned to a plant."""
        result = await session.execute(
            select(func.count(Worker.id)).where(
                Worker.plant_id == plant_id,
                Worker.is_active.is_(True),
            )
        )
        return int(result.scalar_one())

    @staticmethod
    async def _count_active_permits(session: AsyncSession, plant_id: str, now: datetime) -> int:
        """Count active permits whose time window includes now."""
        result = await session.execute(
            select(func.count(Permit.id)).where(
                Permit.plant_id == plant_id,
                Permit.status == PermitStatus.ACTIVE,
                Permit.starts_at <= now,
                Permit.expires_at >= now,
            )
        )
        return int(result.scalar_one())

    @staticmethod
    async def _count_active_maintenance(session: AsyncSession, plant_id: str) -> int:
        """Count currently active maintenance activities."""
        result = await session.execute(
            select(func.count(MaintenanceActivity.id)).where(
                MaintenanceActivity.plant_id == plant_id,
                MaintenanceActivity.status == MaintenanceStatus.ACTIVE,
            )
        )
        return int(result.scalar_one())

    @staticmethod
    async def _latest_sensor_status(
        session: AsyncSession,
        plant_id: str,
        sensor_type: SensorType,
    ) -> StatusSummary:
        """Return the latest reading for a sensor type in a plant."""
        result = await session.execute(
            select(SensorReading, Sensor)
            .join(Sensor, Sensor.id == SensorReading.sensor_id)
            .where(SensorReading.plant_id == plant_id, Sensor.sensor_type == sensor_type)
            .order_by(desc(SensorReading.measured_at))
            .limit(1)
        )
        row = result.one_or_none()
        if row is None:
            return StatusSummary(status="missing", value=None, unit=None, observed_at=None)
        reading, sensor = row
        return StatusSummary(
            status=reading.quality,
            value=float(reading.value),
            unit=sensor.unit,
            observed_at=reading.measured_at,
        )

    @staticmethod
    async def _equipment_health(session: AsyncSession, plant_id: str) -> StatusSummary:
        """Return a compact equipment health summary."""
        total_result = await session.execute(
            select(func.count(Equipment.id)).where(Equipment.plant_id == plant_id)
        )
        impaired_result = await session.execute(
            select(func.count(Equipment.id)).where(
                Equipment.plant_id == plant_id,
                Equipment.status.in_([EquipmentStatus.MAINTENANCE, EquipmentStatus.OFFLINE]),
            )
        )
        total = int(total_result.scalar_one())
        impaired = int(impaired_result.scalar_one())
        status = "nominal" if impaired == 0 else "degraded"
        return StatusSummary(
            status=status,
            value=total - impaired,
            unit="healthy_assets",
            observed_at=None,
        )

    @staticmethod
    async def _count_recent_incidents(session: AsyncSession, plant_id: str, now: datetime) -> int:
        """Count incidents opened in the last 24 hours that are not closed."""
        result = await session.execute(
            select(func.count(Incident.id)).where(
                Incident.plant_id == plant_id,
                Incident.opened_at >= now - timedelta(hours=24),
                Incident.status != IncidentStatus.CLOSED,
            )
        )
        return int(result.scalar_one())

    @staticmethod
    async def _live_event_feed(session: AsyncSession, plant_id: str) -> list[DashboardEvent]:
        """Return a capped feed of recent alerts, incidents, and notifications."""
        alert_rows = await session.execute(
            select(Alert.title, Alert.risk_level, Alert.triggered_at)
            .where(Alert.plant_id == plant_id)
            .order_by(desc(Alert.triggered_at))
            .limit(5)
        )
        incident_rows = await session.execute(
            select(Incident.title, Incident.risk_level, Incident.opened_at)
            .where(Incident.plant_id == plant_id)
            .order_by(desc(Incident.opened_at))
            .limit(5)
        )
        notification_rows = await session.execute(
            select(Notification.title, Notification.severity, Notification.created_at)
            .where(or_(Notification.plant_id == plant_id, Notification.plant_id.is_(None)))
            .order_by(desc(Notification.created_at))
            .limit(5)
        )

        events = [
            DashboardEvent(
                event_type="alert",
                title=title,
                severity=risk_level.value,
                occurred_at=occurred_at,
            )
            for title, risk_level, occurred_at in alert_rows.all()
        ]
        events.extend(
            DashboardEvent(
                event_type="incident",
                title=title,
                severity=risk_level.value,
                occurred_at=occurred_at,
            )
            for title, risk_level, occurred_at in incident_rows.all()
        )
        events.extend(
            DashboardEvent(
                event_type="notification",
                title=title,
                severity=severity,
                occurred_at=created_at,
            )
            for title, severity, created_at in notification_rows.all()
        )
        return sorted(events, key=lambda event: event.occurred_at, reverse=True)[:10]


class _RiskSnapshot:
    """Internal value object for current risk state."""

    def __init__(self, *, score: float, level: RiskLevel) -> None:
        """Store current score and level."""
        self.score = score
        self.level = level
