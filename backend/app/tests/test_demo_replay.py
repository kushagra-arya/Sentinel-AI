"""Regression tests for the deterministic Section 15 demo replay controller."""

import asyncio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.models import Base
from app.services.demo_service import DemoService
from app.services.report_service import ReportService
from app.services.timeline_service import TimelineService


@pytest.fixture()
def session_factory() -> async_sessionmaker[AsyncSession]:
    """Create an isolated async SQLite database for replay tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def setup() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(setup())
    return async_sessionmaker(engine, expire_on_commit=False)


def test_demo_replay_opens_incident_with_timeline_and_report(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Advancing to step 10 must create the alert, incident, timeline, and export."""
    asyncio.run(_assert_demo_replay(session_factory))


async def _assert_demo_replay(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Run async replay assertions inside a sync pytest test."""
    async with session_factory() as session:
        settings = Settings(chroma_url="http://chromadb:8000")
        started = await DemoService.start(
            session,
            settings=settings,
            mode="accelerated",
            speed_multiplier=600,
        )
        assert started.current_step == 1
        assert started.plant_id is not None

        completed = await DemoService.advance(session, settings=settings, target_step=10)
        assert completed.alert_id is not None
        assert completed.incident_id is not None

        timeline = await TimelineService.for_incident(session, incident_id=completed.incident_id)
        event_types = [entry.event_type for entry in timeline.entries]
        assert "maintenance_started" in event_types
        assert "worker_entered_area" in event_types
        assert "compound_alert" in event_types
        assert "notification_sent" in event_types

        report = await ReportService.export_incident_csv(
            session,
            incident_id=completed.incident_id,
        )
        assert report.filename.endswith(".csv")
        assert report.content_base64

        perf = await DemoService.dashboard_performance(session, plant_id=completed.plant_id)
        assert perf.passed is True
