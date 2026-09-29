"""Model-level tests for SentinelAI persistence constraints."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from app.models import Alert, AlertEvidenceLink, Base, Permit, Plant
from app.models.enums import AlertStatus, RiskLevel


@pytest.fixture()
def session() -> Session:
    """Create an isolated in-memory database for model constraint tests."""
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        """Enable SQLite foreign-key behavior to match PostgreSQL tests better."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


def test_required_columns_reject_missing_values(session: Session) -> None:
    """Plant records must reject missing required business identifiers."""
    session.add(Plant(code="PLANT-1", timezone="UTC"))

    with pytest.raises(IntegrityError):
        session.commit()


def test_enum_columns_reject_invalid_values(session: Session) -> None:
    """Permit status must be constrained to known lifecycle states."""
    plant = Plant(name="Refinery 1", code="REF-1", timezone="UTC")
    session.add(plant)
    session.flush()

    session.add(
        Permit(
            plant_id=plant.id,
            permit_number="PTW-001",
            permit_type="hot_work",
            zone="Zone A",
            status="invalid_status",
            starts_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(hours=4),
        )
    )

    with pytest.raises(StatementError):
        session.commit()


def test_alert_evidence_requires_at_least_one_source_record(session: Session) -> None:
    """Alert evidence links must point to a triggering reading, permit, or maintenance record."""
    plant = Plant(name="Chemical Unit", code="CHEM-1", timezone="UTC")
    session.add(plant)
    session.flush()

    alert = Alert(
        plant_id=plant.id,
        risk_level=RiskLevel.HIGH,
        status=AlertStatus.OPEN,
        title="Compound risk",
        message="Gas trend and active work combined into elevated risk.",
        source="rules_engine",
        triggered_at=datetime.now(UTC),
    )
    session.add(alert)
    session.flush()

    session.add(AlertEvidenceLink(alert_id=alert.id, evidence_role="trigger"))

    with pytest.raises(IntegrityError):
        session.commit()


def test_sensor_readings_have_required_time_series_indexes(session: Session) -> None:
    """Sensor readings must support high-volume sensor/time and plant/time queries."""
    indexes = {
        index["name"]: index["column_names"]
        for index in inspect(session.bind).get_indexes("sensor_readings")
    }

    assert indexes["ix_sensor_readings_sensor_measured_at"] == ["sensor_id", "measured_at"]
    assert indexes["ix_sensor_readings_plant_measured_at"] == ["plant_id", "measured_at"]
