"""Deterministic end-to-end demo replay service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import importlib.util
from pathlib import Path
import sys
from time import perf_counter
from types import ModuleType
from typing import Any

from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.ml.rules_engine import CompoundRuleEngine
from app.models.alerts import Alert, AlertEvidenceLink
from app.models.audit_logs import AuditLog
from app.models.chat_history import ChatHistory
from app.models.documents import Document
from app.models.enums import DocumentType, IncidentStatus, RiskLevel, UserRole
from app.models.incidents import Incident, IncidentEvidenceLink
from app.models.notifications import Notification
from app.models.plants import Plant
from app.models.risk_assessments import RiskAssessment
from app.models.users import User
from app.rag.ingestion import DocumentIngestionPipeline
from app.rag.vector_store import ChromaVectorStore
from app.schemas.demo import DemoPerformanceResponse, DemoStatusResponse
from app.services.audit_service import AuditService
from app.services.dashboard_service import DashboardService

DEMO_USER_EMAIL = "demo.admin@sentinelai.local"
DEMO_USER_PASSWORD = "DemoPass123!"
DEMO_RULE_ID = "gas_increasing_maintenance_workers"
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

STEP_NAMES: dict[int, str] = {
    0: "Reset and ready",
    1: "Login and low-risk dashboard",
    2: "Gas slowly increasing",
    3: "Maintenance begins",
    4: "Workers enter affected area",
    5: "Compound high-risk alert raised",
    6: "Heatmap highlights affected zone",
    7: "Timeline reconstructs contributing events",
    8: "AI Assistant explains with citations",
    9: "Emergency panel recommends actions",
    10: "Incident report exported",
}


@dataclass
class DemoReplayState:
    """In-process replay state for one deterministic demo controller."""

    current_step: int = 0
    mode: str = "accelerated"
    speed_multiplier: float = 60.0
    plant_id: str | None = None
    alert_id: str | None = None
    incident_id: str | None = None
    replay_time: datetime | None = None


demo_state = DemoReplayState()


class DemoService:
    """Replay the Section 15 demo flow against real persisted system data."""

    @staticmethod
    async def start(
        session: AsyncSession,
        *,
        settings: Settings,
        mode: str,
        speed_multiplier: float,
    ) -> DemoStatusResponse:
        """Reset demo data, seed baseline state, and return replay status."""
        generator = DemoService._load_generator()
        dataset = generator.generate_dataset()
        result = await generator.seed_database(session, dataset)
        await DemoService._purge_demo_outputs(session, result.plant_id)
        await DemoService._ensure_demo_user(session, result.plant_id)
        await DemoService._seed_low_risk_baseline(session, result.plant_id, dataset)
        await DemoService._seed_demo_corpus(session, settings=settings, plant_id=result.plant_id)
        demo_state.current_step = 1
        demo_state.mode = mode
        demo_state.speed_multiplier = speed_multiplier
        demo_state.plant_id = result.plant_id
        demo_state.alert_id = None
        demo_state.incident_id = None
        demo_state.replay_time = dataset.scenarios[0].starts_at - timedelta(minutes=20)
        await AuditService.record(
            session,
            actor_user_id=None,
            action="demo_replay_started",
            target_entity_type="plant",
            target_entity_id=result.plant_id,
            after_state={"mode": mode, "speed_multiplier": speed_multiplier},
            commit=True,
        )
        return DemoService.status()

    @staticmethod
    async def advance(
        session: AsyncSession,
        *,
        settings: Settings,
        target_step: int,
    ) -> DemoStatusResponse:
        """Advance the deterministic replay to a requested Section 15 step."""
        if demo_state.plant_id is None:
            await DemoService.start(
                session,
                settings=settings,
                mode=demo_state.mode,
                speed_multiplier=demo_state.speed_multiplier,
            )
        generator = DemoService._load_generator()
        scenario = next(
            item for item in generator.scenario_catalog() if item.code == "INC-001"
        )
        target_times = {
            1: scenario.starts_at - timedelta(minutes=20),
            2: scenario.starts_at + timedelta(minutes=6),
            3: scenario.starts_at + timedelta(minutes=10),
            4: scenario.evaluation_at - timedelta(minutes=2),
            5: scenario.evaluation_at,
            6: scenario.evaluation_at + timedelta(seconds=15),
            7: scenario.evaluation_at + timedelta(seconds=30),
            8: scenario.evaluation_at + timedelta(seconds=45),
            9: scenario.evaluation_at + timedelta(minutes=1),
            10: scenario.evaluation_at + timedelta(minutes=2),
        }
        demo_state.current_step = target_step
        demo_state.replay_time = target_times.get(target_step, scenario.evaluation_at)
        if target_step >= 5:
            await DemoService._ensure_incident_opened(session, plant_id=demo_state.plant_id)
        await AuditService.record(
            session,
            actor_user_id=None,
            action="demo_replay_advanced",
            target_entity_type="plant",
            target_entity_id=demo_state.plant_id or "unknown",
            after_state={"step": target_step, "step_name": STEP_NAMES[target_step]},
            commit=True,
        )
        return DemoService.status()

    @staticmethod
    def status() -> DemoStatusResponse:
        """Return current demo replay status without mutating state."""
        return DemoStatusResponse(
            current_step=demo_state.current_step,
            current_step_name=STEP_NAMES[demo_state.current_step],
            mode=demo_state.mode,  # type: ignore[arg-type]
            speed_multiplier=demo_state.speed_multiplier,
            plant_id=demo_state.plant_id,
            plant_code="DEMO-REFINERY-A",
            alert_id=demo_state.alert_id,
            incident_id=demo_state.incident_id,
            demo_user_email=DEMO_USER_EMAIL,
            demo_user_password=DEMO_USER_PASSWORD,
            replay_time=demo_state.replay_time,
        )

    @staticmethod
    async def dashboard_performance(
        session: AsyncSession,
        *,
        plant_id: str,
    ) -> DemoPerformanceResponse:
        """Measure dashboard aggregation against the two-second demo budget."""
        started = perf_counter()
        await DashboardService.get_summary(session, plant_id=plant_id)
        elapsed_ms = (perf_counter() - started) * 1000.0
        return DemoPerformanceResponse(
            plant_id=plant_id,
            elapsed_ms=round(elapsed_ms, 3),
            budget_ms=2000.0,
            passed=elapsed_ms < 2000.0,
        )

    @staticmethod
    async def _purge_demo_outputs(session: AsyncSession, plant_id: str) -> None:
        """Remove replay outputs while preserving synthetic source data."""
        for model in (
            AuditLog,
            ChatHistory,
            Document,
            Notification,
            IncidentEvidenceLink,
            Incident,
            AlertEvidenceLink,
            Alert,
            RiskAssessment,
        ):
            if hasattr(model, "plant_id"):
                await session.execute(delete(model).where(model.plant_id == plant_id))
        await session.commit()

    @staticmethod
    async def _ensure_demo_user(session: AsyncSession, plant_id: str) -> User:
        """Create or update the deterministic demo admin user."""
        user = (
            await session.execute(select(User).where(User.email == DEMO_USER_EMAIL))
        ).scalar_one_or_none()
        if user is None:
            user = User(
                plant_id=plant_id,
                email=DEMO_USER_EMAIL,
                hashed_password=password_context.hash(DEMO_USER_PASSWORD),
                full_name="SentinelAI Demo Admin",
                role=UserRole.ADMIN,
                is_active=True,
            )
            session.add(user)
        else:
            user.plant_id = plant_id
            user.hashed_password = password_context.hash(DEMO_USER_PASSWORD)
            user.role = UserRole.ADMIN
            user.is_active = True
        await session.commit()
        await session.refresh(user)
        return user

    @staticmethod
    async def _seed_low_risk_baseline(
        session: AsyncSession,
        plant_id: str,
        dataset: Any,
    ) -> None:
        """Persist an initial low-risk assessment for step 1."""
        session.add(
            RiskAssessment(
                plant_id=plant_id,
                assessed_at=dataset.scenarios[0].starts_at - timedelta(minutes=20),
                risk_level=RiskLevel.LOW,
                score=0.08,
                rule_ids=[],
                model_name="demo-replay",
                model_version="section-15-v1",
                explanation={"state": "normal_operation"},
            )
        )
        await session.commit()

    @staticmethod
    async def _ensure_incident_opened(session: AsyncSession, *, plant_id: str | None) -> None:
        """Run the real rule engine and open an incident from its evidence chain."""
        if plant_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Demo replay has not been started.",
            )
        existing = (
            await session.execute(
                select(Incident).where(
                    Incident.plant_id == plant_id,
                    Incident.title == "Demo compound gas risk incident",
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            demo_state.incident_id = existing.id
            demo_state.alert_id = existing.primary_alert_id
            return

        generator = DemoService._load_generator()
        scenario = next(
            item for item in generator.scenario_catalog() if item.code == "INC-001"
        )
        findings = await CompoundRuleEngine().evaluate_and_persist(
            session,
            plant_id=plant_id,
            evaluated_at=scenario.evaluation_at,
        )
        if not any(finding.rule_id == DEMO_RULE_ID for finding in findings):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Demo compound rule did not fire.",
            )
        alert = (
            await session.execute(
                select(Alert)
                .where(Alert.plant_id == plant_id, Alert.source == f"rule:{DEMO_RULE_ID}")
                .order_by(Alert.triggered_at.desc())
                .limit(1)
            )
        ).scalar_one()
        alert.triggered_at = scenario.evaluation_at
        incident = Incident(
            plant_id=plant_id,
            primary_alert_id=alert.id,
            risk_level=alert.risk_level,
            status=IncidentStatus.OPEN,
            title="Demo compound gas risk incident",
            summary=(
                "Gas concentration increased while maintenance was active and workers "
                "were present in Zone A."
            ),
            opened_at=scenario.evaluation_at + timedelta(seconds=30),
        )
        session.add(incident)
        await session.flush()
        session.add(
            IncidentEvidenceLink(
                incident_id=incident.id,
                alert_id=alert.id,
                sequence_number=1,
                evidence_role="triggering_alert",
            )
        )
        links = (
            await session.execute(
                select(AlertEvidenceLink).where(AlertEvidenceLink.alert_id == alert.id)
            )
        ).scalars()
        sequence = 2
        for link in links:
            session.add(
                IncidentEvidenceLink(
                    incident_id=incident.id,
                    sensor_reading_id=link.sensor_reading_id,
                    permit_id=link.permit_id,
                    maintenance_activity_id=link.maintenance_activity_id,
                    worker_location_event_id=link.worker_location_event_id,
                    sequence_number=sequence,
                    evidence_role=link.evidence_role,
                )
            )
            sequence += 1
        user = (
            await session.execute(select(User).where(User.email == DEMO_USER_EMAIL))
        ).scalar_one_or_none()
        if user is not None:
            session.add(
                Notification(
                    user_id=user.id,
                    plant_id=plant_id,
                    title="Supervisor notified",
                    body="High compound gas risk alert sent to the supervisor.",
                    severity="high",
                    created_at=scenario.evaluation_at + timedelta(seconds=45),
                    updated_at=scenario.evaluation_at + timedelta(seconds=45),
                )
            )
        demo_state.alert_id = alert.id
        demo_state.incident_id = incident.id
        await session.commit()

    @staticmethod
    async def _seed_demo_corpus(
        session: AsyncSession,
        *,
        settings: Settings,
        plant_id: str,
    ) -> None:
        """Index the safety guidance needed by the AI Assistant demo step."""
        content = (
            "Section 7.4 Gas Maintenance Controls\n"
            "When gas concentration is increasing during maintenance and workers "
            "are present, the supervisor shall remove workers from the affected "
            "zone, pause work, verify isolation, and notify the safety officer."
        )
        existing = (
            await session.execute(
                select(Document).where(
                    Document.plant_id == plant_id,
                    Document.source_uri == "fixture://demo-gas-maintenance-controls",
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return
        try:
            vector_store = ChromaVectorStore(
                chroma_url=settings.chroma_url,
                collection_name=settings.chroma_collection,
            )
            await DocumentIngestionPipeline(vector_store=vector_store).ingest_text(
                session,
                plant_id=plant_id,
                title="Demo Gas Maintenance Controls",
                document_type=DocumentType.SOP,
                source_uri="fixture://demo-gas-maintenance-controls",
                content_text=content,
            )
        except Exception:
            await session.rollback()
            session.add(
                Document(
                    plant_id=plant_id,
                    title="Demo Gas Maintenance Controls",
                    document_type=DocumentType.SOP,
                    source_uri="fixture://demo-gas-maintenance-controls",
                    checksum="demo-unindexed",
                    content_text=content,
                )
            )
            await session.commit()

    @staticmethod
    def _load_generator() -> ModuleType:
        """Load the shared synthetic generator from repo or container layout."""
        seed_path = Path(__file__).resolve()
        candidates = [
            seed_path.parents[2] / "data" / "synthetic" / "generator.py",
            seed_path.parents[3] / "data" / "synthetic" / "generator.py",
        ]
        generator_path = next((path for path in candidates if path.exists()), candidates[-1])
        spec = importlib.util.spec_from_file_location(
            "sentinelai_synthetic_generator_demo",
            generator_path,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load synthetic generator from {generator_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
