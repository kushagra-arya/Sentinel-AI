"""Integration tests for auth, RBAC, dashboard, and notifications."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db_session
from app.core.security import hash_password
from app.main import create_app
from app.models import Base
from app.models.alerts import Alert
from app.models.audit_logs import AuditLog
from app.models.equipment import Equipment
from app.models.enums import (
    AlertStatus,
    EquipmentStatus,
    IncidentStatus,
    MaintenanceStatus,
    PermitStatus,
    RiskLevel,
    SensorStatus,
    SensorType,
    UserRole,
)
from app.models.incidents import Incident
from app.models.maintenance import MaintenanceActivity
from app.models.permits import Permit
from app.models.plants import Plant
from app.models.risk_assessments import RiskAssessment
from app.models.sensor_readings import SensorReading
from app.models.sensors import Sensor
from app.models.users import User
from app.models.workers import Worker


@pytest.fixture()
async def client_and_session() -> AsyncIterator[
    tuple[AsyncClient, async_sessionmaker[AsyncSession]]
]:
    """Create an API client backed by an isolated async SQLite database."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


async def seed_user(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str,
    role: UserRole,
    plant_id: str | None = None,
) -> User:
    """Seed a user for auth and RBAC tests."""
    async with session_factory() as session:
        user = User(
            plant_id=plant_id,
            email=email,
            hashed_password=hash_password("CorrectHorse1"),
            full_name=f"{role.value} user",
            role=role,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def login(client: AsyncClient, email: str) -> dict:
    """Login a seeded user and return the response payload."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "CorrectHorse1"},
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_auth_login_refresh_and_logout_flow(client_and_session) -> None:
    """Users can login, rotate refresh tokens, and logout with audit records."""
    client, session_factory = client_and_session
    await seed_user(session_factory, email="admin@example.com", role=UserRole.ADMIN)

    login_payload = await login(client, "admin@example.com")
    refresh_token = login_payload["tokens"]["refresh_token"]

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 200
    rotated_refresh_token = refresh_response.json()["tokens"]["refresh_token"]
    assert rotated_refresh_token != refresh_token

    logout_response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": rotated_refresh_token},
        headers={"Authorization": f"Bearer {refresh_response.json()['tokens']['access_token']}"},
    )
    assert logout_response.status_code == 200
    assert logout_response.json() == {"status": "logged_out"}

    async with session_factory() as session:
        result = await session.execute(select(AuditLog.action))
        assert {"login", "refresh_token_rotated", "logout"}.issubset(set(result.scalars()))


@pytest.mark.asyncio
async def test_rbac_denial_is_audited(client_and_session) -> None:
    """Viewer role cannot dispatch notifications and denial is audited."""
    client, session_factory = client_and_session
    user = await seed_user(session_factory, email="viewer@example.com", role=UserRole.VIEWER)
    token = (await login(client, "viewer@example.com"))["tokens"]["access_token"]

    response = await client.post(
        "/api/v1/notifications",
        json={
            "user_id": user.id,
            "title": "Denied",
            "body": "Viewer should not dispatch.",
            "channels": ["dashboard"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    async with session_factory() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.action == "permission_denied")
        )
        assert result.scalar_one().actor_user_id == user.id


@pytest.mark.asyncio
async def test_dashboard_aggregation_correctness(client_and_session) -> None:
    """Dashboard summary aggregates current risk, activity, telemetry, and events."""
    client, session_factory = client_and_session
    now = datetime.now(UTC)
    async with session_factory() as session:
        plant = Plant(name="Refinery", code="REF", timezone="UTC")
        session.add(plant)
        await session.flush()
        user = User(
            plant_id=plant.id,
            email="safety@example.com",
            hashed_password=hash_password("CorrectHorse1"),
            full_name="Safety Officer",
            role=UserRole.SAFETY_OFFICER,
            is_active=True,
        )
        equipment = Equipment(
            plant_id=plant.id,
            asset_tag="P-101",
            name="Pump 101",
            equipment_type="pump",
            zone="A",
            status=EquipmentStatus.ACTIVE,
        )
        session.add_all([user, equipment])
        await session.flush()
        gas_sensor = Sensor(
            plant_id=plant.id,
            equipment_id=equipment.id,
            external_id="gas-1",
            name="Gas Sensor",
            sensor_type=SensorType.GAS,
            unit="ppm",
            zone="A",
            x_coordinate=1,
            y_coordinate=1,
            status=SensorStatus.ACTIVE,
        )
        temp_sensor = Sensor(
            plant_id=plant.id,
            equipment_id=equipment.id,
            external_id="temp-1",
            name="Temp Sensor",
            sensor_type=SensorType.TEMPERATURE,
            unit="celsius",
            zone="A",
            x_coordinate=1,
            y_coordinate=2,
            status=SensorStatus.ACTIVE,
        )
        session.add_all([gas_sensor, temp_sensor])
        await session.flush()
        session.add_all(
            [
                Worker(plant_id=plant.id, badge_id="W1", full_name="Worker", role="operator"),
                Permit(
                    plant_id=plant.id,
                    permit_number="PTW-1",
                    permit_type="hot_work",
                    zone="A",
                    status=PermitStatus.ACTIVE,
                    starts_at=now - timedelta(hours=1),
                    expires_at=now + timedelta(hours=1),
                ),
                MaintenanceActivity(
                    plant_id=plant.id,
                    equipment_id=equipment.id,
                    work_order="WO-1",
                    maintenance_type="inspection",
                    zone="A",
                    status=MaintenanceStatus.ACTIVE,
                    starts_at=now - timedelta(minutes=30),
                ),
                SensorReading(
                    plant_id=plant.id,
                    sensor_id=gas_sensor.id,
                    measured_at=now,
                    value=14.5,
                    quality="good",
                ),
                SensorReading(
                    plant_id=plant.id,
                    sensor_id=temp_sensor.id,
                    measured_at=now,
                    value=38.2,
                    quality="good",
                ),
                Alert(
                    plant_id=plant.id,
                    risk_level=RiskLevel.CRITICAL,
                    status=AlertStatus.OPEN,
                    title="Critical gas risk",
                    message="Compound risk.",
                    source="rules_engine",
                    triggered_at=now,
                ),
                Incident(
                    plant_id=plant.id,
                    risk_level=RiskLevel.HIGH,
                    status=IncidentStatus.OPEN,
                    title="Near miss",
                    summary="Worker near maintenance.",
                    opened_at=now,
                ),
                RiskAssessment(
                    plant_id=plant.id,
                    assessed_at=now,
                    risk_level=RiskLevel.HIGH,
                    score=0.82,
                    rule_ids=["gas_maintenance_workers"],
                    model_name="xgboost",
                    model_version="bootstrap",
                    explanation={"inputs": ["gas", "maintenance", "workers"]},
                ),
            ]
        )
        await session.commit()
        plant_id = plant.id

    token = (await login(client, "safety@example.com"))["tokens"]["access_token"]
    response = await client.get(
        f"/api/v1/dashboard/summary?plant_id={plant_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_risk_level"] == "high"
    assert payload["active_alerts"] == 1
    assert payload["critical_alerts"] == 1
    assert payload["worker_count"] == 1
    assert payload["active_permits"] == 1
    assert payload["maintenance_activities"] == 1
    assert payload["gas_status"]["value"] == 14.5
    assert payload["temperature_status"]["value"] == 38.2
    assert payload["recent_incidents"] == 1
    assert payload["live_event_feed"][0]["title"] in {"Critical gas risk", "Near miss"}


@pytest.mark.asyncio
async def test_notification_dispatch_and_listing(client_and_session) -> None:
    """Dashboard and email notification channels dispatch and persist correctly."""
    client, session_factory = client_and_session
    user = await seed_user(
        session_factory,
        email="supervisor@example.com",
        role=UserRole.SUPERVISOR,
    )
    token = (await login(client, "supervisor@example.com"))["tokens"]["access_token"]

    response = await client.post(
        "/api/v1/notifications",
        json={
            "user_id": user.id,
            "title": "Gas trend rising",
            "body": "Review Zone A.",
            "channels": ["dashboard", "email", "sms"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["notification"]["title"] == "Gas trend rising"
    assert {delivery["status"] for delivery in payload["deliveries"]} == {
        "delivered",
        "queued",
        "not_configured",
    }

    list_response = await client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    assert list_response.json()[0]["title"] == "Gas trend rising"
