"""Risk engine API routes for compound rules, classification, and forecasting."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import require_roles
from app.models.enums import UserRole
from app.models.users import User
from app.schemas.risk import (
    RiskClassificationRequest,
    RiskClassificationResponse,
    RiskPredictionResponse,
    RuleEvaluationResponse,
)
from app.services.risk_service import RiskService

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post(
    "/rules/evaluate",
    response_model=RuleEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate compound risk rules",
    description="Runs configured windowed compound-risk rules and persists explainable alerts.",
    openapi_extra={"x-roles": ["admin", "safety_officer", "supervisor"]},
)
async def evaluate_rules(
    plant_id: str = Query(description="Plant identifier to evaluate."),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.SAFETY_OFFICER, UserRole.SUPERVISOR)
    ),
    session: AsyncSession = Depends(get_db_session),
) -> RuleEvaluationResponse:
    """Evaluate all configured compound risk rules for a plant."""
    return await RiskService.evaluate_rules(
        session,
        plant_id=plant_id,
        actor_user_id=current_user.id,
    )


@router.post(
    "/classify",
    response_model=RiskClassificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Classify current plant risk",
    description="Classifies risk from structured features and records model version provenance.",
    openapi_extra={"x-roles": ["admin", "safety_officer", "supervisor"]},
)
async def classify_risk(
    payload: RiskClassificationRequest,
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.SAFETY_OFFICER, UserRole.SUPERVISOR)
    ),
    session: AsyncSession = Depends(get_db_session),
) -> RiskClassificationResponse:
    """Classify a feature vector and persist an auditable risk assessment."""
    return await RiskService.classify(
        session,
        payload=payload,
        actor_user_id=current_user.id,
    )


@router.get(
    "/predictions",
    response_model=RiskPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict telemetry risk trends",
    description="Predicts gas, temperature, and pressure trends thirty minutes ahead.",
    openapi_extra={
        "x-roles": ["admin", "safety_officer", "supervisor", "compliance_officer", "viewer"]
    },
)
async def predict_trends(
    plant_id: str = Query(description="Plant identifier to forecast."),
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
) -> RiskPredictionResponse:
    """Return thirty-minute forecasts for key telemetry signals."""
    del current_user
    return await RiskService.predict_trends(session, plant_id=plant_id)
