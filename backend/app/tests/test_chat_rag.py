"""Tests for retrieval-grounded AI Safety Assistant behavior."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.models import Base
from app.models.chat_history import ChatHistory
from app.models.enums import DocumentType, IncidentStatus, RiskLevel, UserRole
from app.models.incidents import Incident, IncidentEvidenceLink
from app.models.plants import Plant
from app.models.users import User
from app.rag.ingestion import DocumentIngestionPipeline
from app.rag.vector_store import InMemoryVectorStore
from app.schemas.chat import ChatMode, ChatRequest
from app.services.chat_service import ChatService


@pytest.fixture()
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Create an isolated async SQLite database for RAG service tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture()
def settings() -> Settings:
    """Return settings tuned for deterministic in-memory retrieval tests."""
    return Settings(rag_min_confidence=0.05)


async def seed_user_and_plant(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[str, str]:
    """Seed a user and plant for chat persistence tests."""
    async with session_factory() as session:
        plant = Plant(name="RAG Plant", code="RAG", timezone="UTC")
        session.add(plant)
        await session.flush()
        user = User(
            plant_id=plant.id,
            email="rag@example.com",
            hashed_password="not-used",
            full_name="RAG User",
            role=UserRole.SAFETY_OFFICER,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        return user.id, plant.id


async def ingest_fixture_corpus(
    session: AsyncSession,
    vector_store: InMemoryVectorStore,
    plant_id: str,
) -> None:
    """Ingest the small fixture corpus used by retrieval tests."""
    pipeline = DocumentIngestionPipeline(vector_store=vector_store)
    fixture_dir = Path(__file__).parent / "fixtures" / "safety_corpus"
    await pipeline.ingest_text(
        session,
        plant_id=plant_id,
        title="Factory Act Excerpt",
        document_type=DocumentType.REGULATION,
        source_uri="fixture://factory_act",
        content_text=(fixture_dir / "factory_act_excerpt.txt").read_text(encoding="utf-8"),
    )
    await pipeline.ingest_text(
        session,
        plant_id=plant_id,
        title="OISD Ventilation Excerpt",
        document_type=DocumentType.REGULATION,
        source_uri="fixture://oisd_ventilation",
        content_text=(fixture_dir / "oisd_ventilation_excerpt.txt").read_text(encoding="utf-8"),
    )


@pytest.mark.asyncio
async def test_retrieval_relevance_and_citation_presence(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Relevant answers must cite the retrieved document section."""
    user_id, plant_id = await seed_user_and_plant(session_factory)
    vector_store = InMemoryVectorStore()
    async with session_factory() as session:
        await ingest_fixture_corpus(session, vector_store, plant_id)
        response = await ChatService(settings=settings, vector_store=vector_store).answer(
            session,
            payload=ChatRequest(
                plant_id=plant_id,
                conversation_id="conv-1",
                mode=ChatMode.REGULATION,
                question="What does OISD say about ventilation in confined spaces?",
            ),
            user_id=user_id,
        )

        assert response.grounded is True
        assert response.citations
        assert response.citations[0].title in {
            "OISD Ventilation Excerpt",
            "Factory Act Excerpt",
        }
        assert response.citations[0].section != "general"
        history_count = len((await session.execute(select(ChatHistory))).scalars().all())
        assert history_count == 2


@pytest.mark.asyncio
async def test_no_information_response_when_retrieval_is_low_confidence(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Assistant must refuse to answer when no relevant source is available."""
    user_id, plant_id = await seed_user_and_plant(session_factory)
    vector_store = InMemoryVectorStore()
    strict_settings = Settings(rag_min_confidence=0.99)
    async with session_factory() as session:
        await ingest_fixture_corpus(session, vector_store, plant_id)
        response = await ChatService(settings=strict_settings, vector_store=vector_store).answer(
            session,
            payload=ChatRequest(
                plant_id=plant_id,
                conversation_id="conv-2",
                mode=ChatMode.QUESTION,
                question="What is the approved cafeteria menu?",
            ),
            user_id=user_id,
        )

        assert response.grounded is False
        assert response.citations == []
        assert "I do not have information" in response.answer


@pytest.mark.asyncio
async def test_incident_explanation_uses_evidence_chain_and_citations(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Incident explanation should cite retrieved regulation and persist chat turns."""
    user_id, plant_id = await seed_user_and_plant(session_factory)
    vector_store = InMemoryVectorStore()
    async with session_factory() as session:
        await ingest_fixture_corpus(session, vector_store, plant_id)
        incident = Incident(
            plant_id=plant_id,
            risk_level=RiskLevel.CRITICAL,
            status=IncidentStatus.OPEN,
            title="Confined-space ventilation failure",
            summary="Workers were assigned to confined-space activity while ventilation failed.",
            opened_at=datetime.now(UTC),
        )
        session.add(incident)
        await session.flush()
        session.add(
            IncidentEvidenceLink(
                incident_id=incident.id,
                alert_id="alert-1",
                sequence_number=1,
                evidence_role="triggering_alert",
            )
        )
        await session.commit()

        response = await ChatService(settings=settings, vector_store=vector_store).explain_incident(
            session,
            incident_id=incident.id,
            conversation_id="conv-3",
            user_id=user_id,
        )

        assert response.grounded is True
        assert response.citations
        assert "Source:" in response.answer
