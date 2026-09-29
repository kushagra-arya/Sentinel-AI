"""AI Safety Assistant service with retrieval-grounded responses only."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.chat_history import ChatHistory
from app.models.enums import ChatRole
from app.models.incidents import Incident, IncidentEvidenceLink
from app.rag.ingestion import DocumentIngestionPipeline
from app.rag.retrieval import RetrievalService
from app.rag.vector_store import RetrievedChunk, VectorStore
from app.schemas.chat import (
    ChatMode,
    ChatRequest,
    ChatResponse,
    Citation,
    DocumentIngestRequest,
)
from app.services.audit_service import AuditService


class ChatService:
    """Retrieval-only assistant service that refuses ungrounded answers."""

    no_information_answer = (
        "I do not have information on that in the indexed safety corpus. "
        "No operational recommendation can be made without a cited source."
    )

    def __init__(
        self,
        *,
        settings: Settings,
        vector_store: VectorStore | None = None,
    ) -> None:
        """Create a chat service with configurable retrieval storage."""
        self.settings = settings
        self.retrieval = RetrievalService(settings=settings, vector_store=vector_store)
        self.vector_store = self.retrieval.vector_store

    async def ingest_document(
        self,
        session: AsyncSession,
        *,
        payload: DocumentIngestRequest,
        actor_user_id: str,
    ) -> int:
        """Ingest a plain-text document into metadata and vector stores."""
        pipeline = DocumentIngestionPipeline(vector_store=self.vector_store)
        chunks = await pipeline.ingest_text(
            session,
            title=payload.title,
            document_type=payload.document_type,
            source_uri=payload.source_uri,
            content_text=payload.content_text,
            plant_id=payload.plant_id,
        )
        await AuditService.record(
            session,
            actor_user_id=actor_user_id,
            action="document_ingested",
            target_entity_type="document",
            target_entity_id=payload.source_uri,
            after_state={"chunks_indexed": len(chunks), "title": payload.title},
            commit=True,
        )
        return len(chunks)

    async def answer(
        self,
        session: AsyncSession,
        *,
        payload: ChatRequest,
        user_id: str,
    ) -> ChatResponse:
        """Answer a user request only from retrieved document evidence."""
        query = self._mode_query(payload)
        results = self.retrieval.retrieve(query)
        grounded = self.retrieval.has_sufficient_evidence(results)
        citations = self._citations(results if grounded else [])
        answer = self._compose_answer(payload, results) if grounded else self.no_information_answer
        response = ChatResponse(
            answer=answer,
            grounded=grounded,
            citations=citations,
            conversation_id=payload.conversation_id,
        )
        await self._persist_turns(session, payload=payload, user_id=user_id, response=response)
        return response

    async def explain_incident(
        self,
        session: AsyncSession,
        *,
        incident_id: str,
        conversation_id: str,
        user_id: str,
    ) -> ChatResponse:
        """Explain an incident using its evidence chain and retrieved safety guidance."""
        incident = await session.get(Incident, incident_id)
        if incident is None:
            response = ChatResponse(
                answer=self.no_information_answer,
                grounded=False,
                citations=[],
                conversation_id=conversation_id,
            )
            return response

        evidence = await self._incident_evidence(session, incident_id)
        question = (
            f"Explain incident {incident.title}. Risk level {incident.risk_level.value}. "
            f"Summary: {incident.summary}. Evidence: {evidence}."
        )
        payload = ChatRequest(
            plant_id=incident.plant_id,
            conversation_id=conversation_id,
            mode=ChatMode.INCIDENT_EXPLANATION,
            question=question,
        )
        return await self.answer(session, payload=payload, user_id=user_id)

    def _mode_query(self, payload: ChatRequest) -> str:
        """Expand mode-specific query language while staying retrieval-only."""
        prefixes = {
            ChatMode.QUESTION: "Answer from safety corpus:",
            ChatMode.PROCEDURE: "Procedure or SOP lookup:",
            ChatMode.REGULATION: "Regulation clause lookup:",
            ChatMode.INCIDENT_EXPLANATION: "Incident explanation regulation risk:",
            ChatMode.RECOMMENDATION: "Safety recommendation based on procedure:",
        }
        return f"{prefixes[payload.mode]} {payload.question}"

    def _compose_answer(self, payload: ChatRequest, results: list[RetrievedChunk]) -> str:
        """Compose a concise extractive answer from retrieved chunks."""
        top = results[0]
        cited = f"{top.chunk.title}, {top.chunk.section}"
        if payload.mode == ChatMode.RECOMMENDATION:
            lead = "Recommended action based on retrieved guidance"
        elif payload.mode == ChatMode.PROCEDURE:
            lead = "Procedure found in retrieved guidance"
        elif payload.mode == ChatMode.REGULATION:
            lead = "Relevant regulation found"
        elif payload.mode == ChatMode.INCIDENT_EXPLANATION:
            lead = "Incident explanation based on retrieved safety guidance"
        else:
            lead = "Answer based on retrieved safety guidance"
        excerpt = self._safe_excerpt(top.chunk.text)
        return f"{lead}: {excerpt} Source: {cited}."

    @staticmethod
    def _safe_excerpt(text: str, max_chars: int = 420) -> str:
        """Return a short extractive excerpt without over-quoting source text."""
        injection_markers = (
            "ignore previous instructions",
            "system prompt",
            "developer message",
            "disregard the above",
            "<script",
        )
        safe_lines = [
            line
            for line in text.splitlines()
            if not any(marker in line.lower() for marker in injection_markers)
        ]
        compact = " ".join(" ".join(safe_lines).split())
        if len(compact) <= max_chars:
            return compact
        return compact[: max_chars - 3].rstrip() + "..."

    @staticmethod
    def _citations(results: list[RetrievedChunk]) -> list[Citation]:
        """Map retrieved chunks to citation schemas."""
        return [
            Citation(
                document_id=result.chunk.document_id,
                title=result.chunk.title,
                source_uri=result.chunk.source_uri,
                section=result.chunk.section,
                score=result.score,
            )
            for result in results
        ]

    async def _persist_turns(
        self,
        session: AsyncSession,
        *,
        payload: ChatRequest,
        user_id: str,
        response: ChatResponse,
    ) -> None:
        """Persist user and assistant turns to chat history."""
        session.add(
            ChatHistory(
                user_id=user_id,
                plant_id=payload.plant_id,
                conversation_id=payload.conversation_id,
                role=ChatRole.USER,
                content=payload.question,
                citations=[],
            )
        )
        session.add(
            ChatHistory(
                user_id=user_id,
                plant_id=payload.plant_id,
                conversation_id=payload.conversation_id,
                role=ChatRole.ASSISTANT,
                content=response.answer,
                citations=[citation.model_dump() for citation in response.citations],
            )
        )
        await AuditService.record(
            session,
            actor_user_id=user_id,
            action="chat_turn_persisted",
            target_entity_type="conversation",
            target_entity_id=payload.conversation_id,
            after_state={
                "mode": payload.mode.value,
                "grounded": response.grounded,
                "citation_count": len(response.citations),
                "question_length": len(payload.question),
            },
        )
        await session.commit()

    @staticmethod
    async def _incident_evidence(session: AsyncSession, incident_id: str) -> list[dict]:
        """Return persisted incident evidence links as plain dictionaries."""
        result = await session.execute(
            select(IncidentEvidenceLink).where(IncidentEvidenceLink.incident_id == incident_id)
        )
        evidence = []
        for link in result.scalars():
            evidence.append(
                {
                    "alert_id": link.alert_id,
                    "sensor_reading_id": link.sensor_reading_id,
                    "permit_id": link.permit_id,
                    "maintenance_activity_id": link.maintenance_activity_id,
                    "worker_location_event_id": link.worker_location_event_id,
                    "role": link.evidence_role,
                    "sequence": link.sequence_number,
                }
            )
        return evidence
