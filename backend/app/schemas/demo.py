"""Schemas for deterministic SentinelAI demo replay control."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


DemoReplayMode = Literal["realtime", "accelerated"]


class DemoStartRequest(BaseModel):
    """Request to reset and start the deterministic demo replay."""

    mode: DemoReplayMode = Field(default="accelerated", description="Replay timing mode.")
    speed_multiplier: float = Field(
        default=60.0,
        ge=0.1,
        le=10_000.0,
        description="Replay speed multiplier for accelerated mode.",
    )


class DemoAdvanceRequest(BaseModel):
    """Request to advance the replay to a specific demo step."""

    step: int = Field(ge=0, le=10, description="Target demo step from the Section 15 flow.")


class DemoStatusResponse(BaseModel):
    """Current deterministic demo replay state."""

    current_step: int = Field(description="Current Section 15 demo step.")
    current_step_name: str = Field(description="Human-readable current step name.")
    mode: DemoReplayMode = Field(description="Replay timing mode.")
    speed_multiplier: float = Field(description="Replay speed multiplier.")
    plant_id: str | None = Field(description="Demo plant identifier.")
    plant_code: str = Field(description="Demo plant code.")
    alert_id: str | None = Field(description="Compound alert identifier after step 5.")
    incident_id: str | None = Field(description="Incident identifier after step 5.")
    demo_user_email: str = Field(description="Seeded demo user email.")
    demo_user_password: str = Field(description="Seeded demo user password.")
    replay_time: datetime | None = Field(description="Synthetic timeline time represented now.")


class DemoPerformanceResponse(BaseModel):
    """Dashboard performance check result for demo-scale data."""

    plant_id: str = Field(description="Measured plant identifier.")
    elapsed_ms: float = Field(description="Dashboard aggregation duration in milliseconds.")
    budget_ms: float = Field(description="Allowed response budget in milliseconds.")
    passed: bool = Field(description="Whether the aggregation met the budget.")
