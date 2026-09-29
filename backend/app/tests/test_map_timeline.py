"""Tests for map and forensic timeline services."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models import Base
from app.models.alerts import Alert, AlertEvidenceLink
from app.models.enums import (
    AlertStatus,
    EquipmentStatus,
    IncidentStatus,
    MaintenanceStatus,
    RiskLevel,
    SensorStatus,
    SensorType,
)
from app.models.equipment import Equipment
from app.models.incidents import Incident, IncidentEvidenceLink
from app.models.maintenance import MaintenanceActivity
from app.models.notifications import Notification
from app.models.plants import Plant
from app.models.sensor_readings import SensorReading
from app.models.sensors import Sensor
from app.models.users import User
from app.models.workers import Worker, WorkerLocationEvent
from app.schemas.map import MapViewportRequest
from app.services.map_service import MapService
from app.services.timeline_service import TimelineService


@pytest.fixture()
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Create an isolated async SQLite database for map/timeline tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_alert_marker_and_heatmap_use_alert_evidence(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Alert markers and heatmap cells should be computed from evidence locations."""
    now = datetime.now(UTC)
    async with session_factory() as session:
        plant, sensor, reading, alert = await _seed_compound_alert(session, now)
        session.add(
            AlertEvidenceLink(
                alert_id=alert.id,
                sensor_reading_id=reading.id,
                evidence_role="gas_window_end",
            )
        )
        await session.commit()

        markers = await MapService.alert_markers(session, plant_id=plant.id)
        viewport = await MapService.get_viewport(
            session,
            payload=MapViewportRequest(
                plant_id=plant.id,
                zoom=1,
                min_x=0,
                min_y=0,
                max_x=20,
                max_y=20,
                layers=["alerts", "heatmap"],
            ),
        )

        assert markers[0].coordinate is not None
        assert markers[0].coordinate.x == float(sensor.x_coordinate)
        assert viewport.heatmap
        assert alert.id in viewport.heatmap[0].contributing_alert_ids


@pytest.mark.asyncio
async def test_incident_timeline_reconstructs_order_and_evidence_links(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Timeline must reconstruct the compound-alert sequence from evidence links."""
    base_time = datetime.now(UTC)
    async with session_factory() as session:
        plant, _sensor, first_reading, alert = await _seed_compound_alert(session, base_time)
        maintenance = MaintenanceActivity(
            plant_id=plant.id,
            work_order="WO-TL-1",
            maintenance_type="pump inspection",
            zone="Zone A",
            status=MaintenanceStatus.ACTIVE,
            starts_at=base_time + timedelta(minutes=5),
        )
        worker = Worker(
            plant_id=plant.id,
            badge_id="TL-W1",
            full_name="Timeline Worker",
            role="operator",
        )
        session.add_all([maintenance, worker])
        await session.flush()
        worker_event = WorkerLocationEvent(
            plant_id=plant.id,
            worker_id=worker.id,
            zone="Zone A",
            x_coordinate=7,
            y_coordinate=8,
            observed_at=base_time + timedelta(minutes=10),
        )
        notification_user = User(
            plant_id=plant.id,
            email="timeline@example.com",
            hashed_password="not-used",
            full_name="Supervisor",
            role="supervisor",
            is_active=True,
        )
        session.add_all([worker_event, notification_user])
        await session.flush()
        notification = Notification(
            plant_id=plant.id,
            user_id=notification_user.id,
            title="Supervisor notified",
            body="Supervisor notified about compound gas risk.",
            severity="high",
        )
        incident = Incident(
            plant_id=plant.id,
            primary_alert_id=alert.id,
            risk_level=RiskLevel.HIGH,
            status=IncidentStatus.OPEN,
            title="Compound gas incident",
            summary="Gas increased while maintenance was active and workers were nearby.",
            opened_at=base_time + timedelta(minutes=16),
        )
        session.add_all([notification, incident])
        await session.flush()
        session.add_all(
            [
                AlertEvidenceLink(
                    alert_id=alert.id,
                    sensor_reading_id=first_reading.id,
                    evidence_role="gas_begins_increasing",
                ),
                AlertEvidenceLink(
                    alert_id=alert.id,
                    maintenance_activity_id=maintenance.id,
                    evidence_role="maintenance_active",
                ),
                AlertEvidenceLink(
                    alert_id=alert.id,
                    worker_location_event_id=worker_event.id,
                    evidence_role="workers_nearby",
                ),
                IncidentEvidenceLink(
                    incident_id=incident.id,
                    sensor_reading_id=first_reading.id,
                    sequence_number=1,
                    evidence_role="gas_begins_increasing",
                ),
                IncidentEvidenceLink(
                    incident_id=incident.id,
                    maintenance_activity_id=maintenance.id,
                    sequence_number=2,
                    evidence_role="maintenance_active",
                ),
                IncidentEvidenceLink(
                    incident_id=incident.id,
                    worker_location_event_id=worker_event.id,
                    sequence_number=3,
                    evidence_role="workers_nearby",
                ),
                IncidentEvidenceLink(
                    incident_id=incident.id,
                    alert_id=alert.id,
                    sequence_number=4,
                    evidence_role="compound_alert",
                ),
            ]
        )
        await session.commit()

        timeline = await TimelineService.for_incident(session, incident_id=incident.id)

        occurred = [entry.occurred_at for entry in timeline.entries]
        assert occurred == sorted(occurred)
        event_types = [entry.event_type for entry in timeline.entries]
        assert "sensor_reading" in event_types
        assert "maintenance_started" in event_types
        assert "worker_entered_area" in event_types
        assert "compound_alert" in event_types
        assert "notification_sent" in event_types
        assert all(entry.evidence.api_path.startswith("/api/v1/") for entry in timeline.entries)


async def _seed_compound_alert(
    session: AsyncSession,
    now: datetime,
) -> tuple[Plant, Sensor, SensorReading, Alert]:
    """Seed a minimal plant, sensor reading, and alert for map/timeline tests."""
    suffix = uuid4().hex[:8]
    plant = Plant(name=f"Map Plant {suffix}", code=f"MAP-{suffix}", timezone="UTC")
    session.add(plant)
    await session.flush()
    equipment = Equipment(
        plant_id=plant.id,
        asset_tag=f"EQ-{suffix}",
        name="Compressor",
        equipment_type="compressor",
        zone="Zone A",
        status=EquipmentStatus.ACTIVE,
    )
    session.add(equipment)
    await session.flush()
    sensor = Sensor(
        plant_id=plant.id,
        equipment_id=equipment.id,
        external_id=f"S-{suffix}",
        name="Gas Sensor",
        sensor_type=SensorType.GAS,
        unit="ppm",
        zone="Zone A",
        x_coordinate=6,
        y_coordinate=7,
        status=SensorStatus.ACTIVE,
    )
    session.add(sensor)
    await session.flush()
    reading = SensorReading(
        plant_id=plant.id,
        sensor_id=sensor.id,
        measured_at=now,
        value=24,
        quality="good",
    )
    alert = Alert(
        plant_id=plant.id,
        risk_level=RiskLevel.HIGH,
        status=AlertStatus.OPEN,
        title="Compound gas risk",
        message="Gas increased while maintenance and workers were nearby.",
        source="rule:gas_increasing_maintenance_workers",
        triggered_at=now + timedelta(minutes=15),
    )
    session.add_all([reading, alert])
    await session.flush()
    return plant, sensor, reading, alert
