"""Tests for emergency panel and incident report generation."""

from base64 import b64decode
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models import Base
from app.models.alerts import Alert
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
from app.models.plants import Plant
from app.models.sensor_readings import SensorReading
from app.models.sensors import Sensor
from app.models.workers import Worker, WorkerLocationEvent
from app.services.report_service import ReportService


@pytest.fixture()
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Create an isolated async SQLite database for report tests."""
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
async def test_incident_report_matches_underlying_evidence(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Generated report and CSV export must match the exact linked evidence records."""
    async with session_factory() as session:
        seeded = await _seed_incident(session)

        report = await ReportService.incident_report(session, incident_id=seeded["incident_id"])
        csv_export = await ReportService.export_incident_csv(
            session,
            incident_id=seeded["incident_id"],
        )
        pdf_export = await ReportService.export_incident_pdf(
            session,
            incident_id=seeded["incident_id"],
        )

        evidence_ids = {item.entity_id for item in report.evidence_summary}
        assert seeded["reading_id"] in evidence_ids
        assert seeded["maintenance_id"] in evidence_ids
        assert report.panel.affected_area == "Zone A"
        assert report.panel.workers_present[0].worker_id == seeded["worker_id"]
        assert report.panel.nearby_equipment[0].equipment_id == seeded["equipment_id"]
        assert report.triggering_rules == ["gas_increasing_maintenance_workers"]
        assert report.action_checklist[0].role == "Supervisor"

        csv_text = b64decode(csv_export.content_base64).decode("utf-8")
        assert seeded["reading_id"] in csv_text
        assert seeded["maintenance_id"] in csv_text
        assert seeded["incident_id"] in b64decode(pdf_export.content_base64).decode("latin-1")


async def _seed_incident(session: AsyncSession) -> dict[str, str]:
    """Seed a compound gas incident with linked evidence."""
    now = datetime.now(UTC)
    plant = Plant(name="Report Plant", code=f"RPT-{int(now.timestamp())}", timezone="UTC")
    session.add(plant)
    await session.flush()
    equipment = Equipment(
        plant_id=plant.id,
        asset_tag=f"EQ-RPT-{int(now.timestamp())}",
        name="Pump P-17",
        equipment_type="pump",
        zone="Zone A",
        status=EquipmentStatus.ACTIVE,
    )
    worker = Worker(
        plant_id=plant.id,
        badge_id=f"W-RPT-{int(now.timestamp())}",
        full_name="Field Operator",
        role="operator",
    )
    session.add_all([equipment, worker])
    await session.flush()
    sensor = Sensor(
        plant_id=plant.id,
        equipment_id=equipment.id,
        external_id=f"S-RPT-{int(now.timestamp())}",
        name="Gas Sensor",
        sensor_type=SensorType.GAS,
        unit="ppm",
        zone="Zone A",
        x_coordinate=1,
        y_coordinate=1,
        status=SensorStatus.ACTIVE,
    )
    session.add(sensor)
    await session.flush()
    reading = SensorReading(
        plant_id=plant.id,
        sensor_id=sensor.id,
        measured_at=now,
        value=42,
        quality="good",
    )
    maintenance = MaintenanceActivity(
        plant_id=plant.id,
        equipment_id=equipment.id,
        work_order=f"WO-RPT-{int(now.timestamp())}",
        maintenance_type="inspection",
        zone="Zone A",
        status=MaintenanceStatus.ACTIVE,
        starts_at=now - timedelta(minutes=5),
    )
    worker_event = WorkerLocationEvent(
        plant_id=plant.id,
        worker_id=worker.id,
        zone="Zone A",
        x_coordinate=2,
        y_coordinate=2,
        observed_at=now + timedelta(minutes=1),
    )
    alert = Alert(
        plant_id=plant.id,
        risk_level=RiskLevel.HIGH,
        status=AlertStatus.OPEN,
        title="High compound gas risk",
        message="Gas rising with maintenance and workers nearby.",
        source="rule:gas_increasing_maintenance_workers",
        triggered_at=now + timedelta(minutes=2),
    )
    session.add_all([reading, maintenance, worker_event, alert])
    await session.flush()
    incident = Incident(
        plant_id=plant.id,
        primary_alert_id=alert.id,
        risk_level=RiskLevel.HIGH,
        status=IncidentStatus.OPEN,
        title="Compound gas incident",
        summary="Gas rose during maintenance while workers were nearby.",
        opened_at=now + timedelta(minutes=3),
    )
    session.add(incident)
    await session.flush()
    session.add_all(
        [
            IncidentEvidenceLink(
                incident_id=incident.id,
                alert_id=alert.id,
                sequence_number=1,
                evidence_role="triggering_alert",
            ),
            IncidentEvidenceLink(
                incident_id=incident.id,
                sensor_reading_id=reading.id,
                sequence_number=2,
                evidence_role="gas_reading",
            ),
            IncidentEvidenceLink(
                incident_id=incident.id,
                maintenance_activity_id=maintenance.id,
                sequence_number=3,
                evidence_role="maintenance_active",
            ),
            IncidentEvidenceLink(
                incident_id=incident.id,
                worker_location_event_id=worker_event.id,
                sequence_number=4,
                evidence_role="worker_nearby",
            ),
        ]
    )
    await session.commit()
    return {
        "incident_id": incident.id,
        "reading_id": reading.id,
        "maintenance_id": maintenance.id,
        "worker_id": worker.id,
        "equipment_id": equipment.id,
    }
