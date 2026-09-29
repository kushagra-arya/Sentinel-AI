"""Pydantic schemas for the AI Safety Assistant."""

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.models.enums import DocumentType


class ChatMode(StrEnum):
    """Supported retrieval-backed assistant modes."""

    QUESTION = "question"
    PROCEDURE = "procedure"
    REGULATION = "regulation"
    INCIDENT_EXPLANATION = "incident_explanation"
    RECOMMENDATION = "recommendation"


class Citation(BaseModel):
    """Source citation required for every grounded assistant answer."""

    document_id: str = Field(description="Source document identifier.")
    title: str = Field(description="Source document title.")
    source_uri: str = Field(description="Source document URI.")
    section: str = Field(description="Section or clause used as evidence.")
    score: float = Field(description="Retrieval confidence score.")


class ChatRequest(BaseModel):
    """Request to ask a retrieval-grounded assistant question."""

    plant_id: str | None = Field(default=None, max_length=64, description="Optional plant scope.")
    conversation_id: str = Field(
        min_length=1,
        max_length=120,
        pattern=r"^[A-Za-z0-9_.:-]+$",
        description="Conversation identifier for persistence.",
    )
    mode: ChatMode = Field(default=ChatMode.QUESTION, description="Assistant task mode.")
    question: str = Field(min_length=1, max_length=2000, description="User question or task.")

    @field_validator("question")
    @classmethod
    def reject_control_characters(cls, value: str) -> str:
        """Reject control characters that can hide prompt-injection payloads."""
        if any(ord(character) < 32 and character not in {"\n", "\r", "\t"} for character in value):
            raise ValueError("Question contains unsupported control characters.")
        return value.strip()


class ChatResponse(BaseModel):
    """Assistant response with mandatory citation metadata."""

    answer: str = Field(description="Grounded answer or explicit no-information response.")
    grounded: bool = Field(description="Whether the answer is grounded in retrieved sources.")
    citations: list[Citation] = Field(description="Source citations supporting the answer.")
    conversation_id: str = Field(description="Conversation identifier.")


class DocumentIngestRequest(BaseModel):
    """Plain-text document ingestion request."""

    plant_id: str | None = Field(default=None, max_length=64, description="Optional plant scope.")
    title: str = Field(min_length=1, max_length=180, description="Document title.")
    document_type: DocumentType = Field(description="Regulated corpus document type.")
    source_uri: str = Field(
        min_length=1,
        max_length=500,
        description="Original source URI or filename.",
    )
    content_text: str = Field(
        min_length=1,
        max_length=200_000,
        description="Extracted text content.",
    )

    @field_validator("content_text")
    @classmethod
    def reject_binary_document_payloads(cls, value: str) -> str:
        """Reject binary/control payloads before indexing into retrieval storage."""
        if "\x00" in value:
            raise ValueError("Document content contains null bytes.")
        return value

    @field_validator("source_uri")
    @classmethod
    def reject_unsafe_source_uri(cls, value: str) -> str:
        """Reject traversal-style source URIs without relying on regex look-arounds."""
        if ".." in value or "\\" in value:
            raise ValueError("Source URI must not contain path traversal segments.")
        return value


class DocumentIngestResponse(BaseModel):
    """Document ingestion response."""

    chunks_indexed: int = Field(description="Number of retrieval chunks indexed.")
