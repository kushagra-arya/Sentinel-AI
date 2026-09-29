"""Pydantic schemas for risk engine API endpoints."""

from pydantic import BaseModel, Field

from app.models.enums import RiskLevel


class EvidenceItem(BaseModel):
    """Evidence item returned for a compound-rule firing."""

    evidence_type: str = Field(min_length=1, max_length=80, description="Evidence source type.")
    record_id: str = Field(
        min_length=1,
        max_length=64,
        description="Persisted source record identifier.",
    )
    role: str = Field(
        min_length=1,
        max_length=120,
        description="Role the source record played in the rule firing.",
    )


class RuleFindingResponse(BaseModel):
    """Response describing a fired compound risk rule."""

    rule_id: str = Field(description="Configured rule identifier.")
    name: str = Field(description="Human-readable rule name.")
    risk_level: RiskLevel = Field(description="Risk level assigned by the rule.")
    title: str = Field(description="Alert title.")
    message: str = Field(description="Explainable alert message.")
    evidence: list[EvidenceItem] = Field(description="Exact evidence records satisfying the rule.")


class RuleEvaluationResponse(BaseModel):
    """Response for a rule-engine evaluation run."""

    plant_id: str = Field(description="Evaluated plant identifier.")
    findings: list[RuleFindingResponse] = Field(description="Rule findings that fired.")


class RiskClassificationRequest(BaseModel):
    """Feature payload for model-based risk classification."""

    plant_id: str = Field(
        min_length=1,
        max_length=64,
        description="Plant identifier for assessment audit persistence.",
    )
    gas: float = Field(ge=0, le=10_000, description="Gas concentration feature.")
    temperature: float = Field(ge=-100, le=500, description="Temperature feature.")
    pressure: float = Field(ge=0, le=1_000, description="Pressure feature.")
    humidity: float = Field(ge=0, le=100, description="Humidity feature.")
    worker_count: int = Field(ge=0, le=10_000, description="Workers in the relevant zone.")
    maintenance_active: bool = Field(description="Whether maintenance is active.")
    permit_type: str = Field(
        default="none",
        max_length=120,
        description="Active permit type, or none.",
    )


class RiskClassificationResponse(BaseModel):
    """Model-based risk classification response."""

    plant_id: str = Field(description="Plant identifier.")
    risk_level: RiskLevel = Field(description="Predicted risk level.")
    score: float = Field(description="Classifier confidence or fallback score.")
    model_name: str = Field(description="Model implementation used.")
    model_version: str = Field(description="Version recorded for auditability.")


class TrendPredictionResponse(BaseModel):
    """Thirty-minute trend prediction for one telemetry signal."""

    signal: str = Field(description="Telemetry signal name.")
    predicted_value: float = Field(description="Predicted value at horizon.")
    horizon_minutes: int = Field(description="Prediction horizon.")
    trend: str = Field(description="Increasing, decreasing, flat, or insufficient_data.")
    risk_level: RiskLevel = Field(description="Forward-looking risk level.")
    minutes_to_high_risk: int | None = Field(
        description="Estimated minutes until high-risk threshold, if crossing."
    )


class RiskPredictionResponse(BaseModel):
    """Risk prediction response for dashboard forward signal."""

    plant_id: str = Field(description="Plant identifier.")
    predictions: list[TrendPredictionResponse] = Field(description="Signal forecasts.")
