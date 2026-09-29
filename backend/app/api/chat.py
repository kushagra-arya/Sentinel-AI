"""AI Safety Assistant API routes."""

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.rate_limit import rate_limit
from app.core.security import require_roles
from app.models.enums import UserRole
from app.models.users import User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    DocumentIngestRequest,
    DocumentIngestResponse,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/documents",
    response_model=DocumentIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a safety document",
    description=(
        "Indexes a plain-text safety document into PostgreSQL metadata "
        "and ChromaDB vectors."
    ),
    openapi_extra={"x-roles": ["admin", "safety_officer", "compliance_officer"]},
)
async def ingest_document(
    payload: DocumentIngestRequest,
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.SAFETY_OFFICER, UserRole.COMPLIANCE_OFFICER)
    ),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> DocumentIngestResponse:
    """Ingest a safety document for retrieval-grounded assistant answers."""
    chunks_indexed = await ChatService(settings=settings).ingest_document(
        session,
        payload=payload,
        actor_user_id=current_user.id,
    )
    return DocumentIngestResponse(chunks_indexed=chunks_indexed)


@router.post(
    "/query",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask the AI Safety Assistant",
    description="Answers questions only from retrieved safety documents and returns citations.",
    openapi_extra={
        "x-roles": ["admin", "safety_officer", "supervisor", "compliance_officer", "viewer"]
    },
)
async def ask_assistant(
    payload: ChatRequest,
    _rate_limited: None = Depends(rate_limit("chat")),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.SAFETY_OFFICER,
            UserRole.SUPERVISOR,
            UserRole.COMPLIANCE_OFFICER,
            UserRole.VIEWER,
        )
    ),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    """Return a retrieval-grounded assistant answer with citations."""
    return await ChatService(settings=settings).answer(
        session,
        payload=payload,
        user_id=current_user.id,
    )


@router.post(
    "/incidents/{incident_id}/explain",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Explain an incident from evidence and citations",
    description=(
        "Explains a stored incident using its evidence chain and retrieved safety guidance."
    ),
    openapi_extra={"x-roles": ["admin", "safety_officer", "supervisor", "compliance_officer"]},
)
async def explain_incident(
    incident_id: str = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$"),
    conversation_id: str = Query(
        min_length=1,
        max_length=120,
        pattern=r"^[A-Za-z0-9_.:-]+$",
        description="Conversation identifier for persistence.",
    ),
    _rate_limited: None = Depends(rate_limit("chat")),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.SAFETY_OFFICER,
            UserRole.SUPERVISOR,
            UserRole.COMPLIANCE_OFFICER,
        )
    ),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    """Explain an incident using persisted evidence and retrieved regulations."""
    return await ChatService(settings=settings).explain_incident(
        session,
        incident_id=incident_id,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
