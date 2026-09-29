"""Pydantic schemas for health-check responses."""

from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    """Response payload for backend liveness checks."""

    status: str = Field(description="Service liveness state.")
    service: str = Field(description="Service name.")


class ReadinessResponse(BaseModel):
    """Response payload for dependency readiness checks."""

    status: str = Field(description="Overall readiness state.")
    database: str = Field(description="Database dependency state.")
