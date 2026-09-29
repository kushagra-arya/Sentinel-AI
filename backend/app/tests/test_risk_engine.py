"""Tests for compound risk rule evaluation and evidence persistence."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.ml.risk_classifier import RiskClassifier, RiskFeatures
from app.ml.rules_engine import CompoundRuleEngine
from app.ml.timeseries_predictor import TimeSeriesPredictor, TrendPoint
from app.models import Base
from app.models.alerts import Alert, AlertEvidenceLink
from app.models.enums import EquipmentStatus, MaintenanceStatus, SensorStatus, SensorType
from app.models.equipment import Equipment
from app.models.maintenance import MaintenanceActivity
from app.models.plants import Plant
from app.models.sensor_readings import SensorReading
from app.models.sensors import Sensor
from app.models.workers import Worker, WorkerLocationEvent


@pytest.fixture()
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Create an isolated async SQLite database for risk engine tests."""
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
async def test_gas_maintenance_worker_rule_persists_complete_evidence_chain(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """A full compound rule firing must persist every contributing evidence record."""
    now = datetime.now(UTC)
    async with session_factory() as session:
        plant = Plant(name="Refinery", code="REF-RISK", timezone="UTC")
        session.add(plant)
        await session.flush()
        equipment = Equipment(
            plant_id=plant.id,
            asset_tag="VESSEL-1",
            name="Process Vessel",
            equipment_type="vessel",
            zone="Zone A",
            status=EquipmentStatus.ACTIVE,
        )
        worker = Worker(
            plant_id=plant.id,
            badge_id="BW-1",
            full_name="Field Operator",
            role="operator",
            is_active=True,
        )
        session.add_all([equipment, worker])
        await session.flush()
        sensor = Sensor(
            plant_id=plant.id,
            equipment_id=equipment.id,
            external_id="GAS-RISK-1",
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
        first_reading = SensorReading(
            plant_id=plant.id,
            sensor_id=sensor.id,
            measured_at=now - timedelta(minutes=10),
            value=10,
            quality="good",
        )
        last_reading = SensorReading(
            plant_id=plant.id,
            sensor_id=sensor.id,
            measured_at=now,
            value=19,
            quality="good",
        )
        maintenance = MaintenanceActivity(
            plant_id=plant.id,
            equipment_id=equipment.id,
            work_order="WO-RISK-1",
            maintenance_type="inspection",
            zone="Zone A",
            status=MaintenanceStatus.ACTIVE,
            starts_at=now - timedelta(minutes=20),
        )
        worker_location = WorkerLocationEvent(
            plant_id=plant.id,
            worker_id=worker.id,
            zone="Zone A",
            x_coordinate=2,
            y_coordinate=2,
            observed_at=now - timedelta(minutes=1),
        )
        session.add_all([first_reading, last_reading, maintenance, worker_location])
        await session.commit()

        findings = await CompoundRuleEngine().evaluate_and_persist(
            session,
            plant_id=plant.id,
            evaluated_at=now,
        )

        assert [finding.rule_id for finding in findings] == ["gas_increasing_maintenance_workers"]
        alert = (await session.execute(select(Alert))).scalar_one()
        evidence_links = (await session.execute(select(AlertEvidenceLink))).scalars().all()
        assert alert.source == "rule:gas_increasing_maintenance_workers"
        assert {link.sensor_reading_id for link in evidence_links if link.sensor_reading_id} == {
            first_reading.id,
            last_reading.id,
        }
        maintenance_ids = {
            link.maintenance_activity_id
            for link in evidence_links
            if link.maintenance_activity_id
        }
        worker_location_ids = {
            link.worker_location_event_id
            for link in evidence_links
            if link.worker_location_event_id
        }
        assert maintenance_ids == {maintenance.id}
        assert worker_location_ids == {worker_location.id}


def test_risk_classifier_fallback_records_model_version() -> None:
    """Classifier fallback must still return auditable model provenance."""
    classifier = RiskClassifier(model_path=__import__("pathlib").Path("missing-risk-model.pkl"))
    prediction = classifier.predict(
        RiskFeatures(
            gas=42,
            temperature=78,
            pressure=118,
            humidity=40,
            worker_count=2,
            maintenance_active=True,
            permit_type="confined_space",
        )
    )

    assert prediction.risk_level.value in {"high", "critical"}
    assert prediction.model_version == "risk-classifier-bootstrap-v1"


def test_timeseries_predictor_reports_minutes_to_high_risk() -> None:
    """Trend predictor should surface forward high-risk timing when crossing threshold."""
    now = datetime.now(UTC)
    prediction = TimeSeriesPredictor().predict(
        "gas",
        [
            TrendPoint(measured_at=now - timedelta(minutes=10), value=30),
            TrendPoint(measured_at=now, value=45),
        ],
    )

    assert prediction.trend == "increasing"
    assert prediction.risk_level.value == "high"
    assert prediction.minutes_to_high_risk is not None
