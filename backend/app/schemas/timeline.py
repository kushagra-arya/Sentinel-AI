"""Pydantic schemas for forensic timeline reconstruction."""

from datetime import datetime
from pydantic import BaseModel, Field


class TimelineEvidenceLink(BaseModel):
    """Clickable evidence link for a timeline event."""

    entity_type: str = Field(description="Evidence entity type.")
    entity_id: str = Field(description="Evidence entity identifier.")
    api_path: str = Field(description="API path clients can use to inspect the evidence.")


class TimelineEntry(BaseModel):
    """Chronological incident or alert timeline entry."""

    occurred_at: datetime = Field(description="Event occurrence timestamp.")
    event_type: str = Field(description="Timeline event type.")
    title: str = Field(description="Generated event title.")
    description: str = Field(description="Generated event description.")
    evidence: TimelineEvidenceLink = Field(description="Supporting evidence link.")


class TimelineResponse(BaseModel):
    """Timeline reconstructed from stored evidence links."""

    subject_type: str = Field(description="incident or alert.")
    subject_id: str = Field(description="Incident or alert identifier.")
    entries: list[TimelineEntry] = Field(description="Chronological generated entries.")
