"""Risk service orchestration for rules, classification, and forecasting."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.risk_classifier import RiskClassifier, RiskFeatures
from app.ml.rules_engine import CompoundRuleEngine
from app.ml.timeseries_predictor import TimeSeriesPredictor, TrendPoint
from app.models.enums import SensorType
from app.models.risk_assessments import RiskAssessment
from app.models.sensor_readings import SensorReading
from app.models.sensors import Sensor
from app.schemas.risk import (
    EvidenceItem,
    RiskClassificationRequest,
    RiskClassificationResponse,
    RiskPredictionResponse,
    RuleEvaluationResponse,
    RuleFindingResponse,
    TrendPredictionResponse,
)
from app.services.audit_service import AuditService


class RiskService:
    """Application service for explainable risk evaluation workflows."""

    @staticmethod
    async def evaluate_rules(
        session: AsyncSession,
        *,
        plant_id: str,
        actor_user_id: str,
    ) -> RuleEvaluationResponse:
        """Evaluate configured compound rules and audit the operation."""
        findings = await CompoundRuleEngine().evaluate_and_persist(session, plant_id=plant_id)
        await AuditService.record(
            session,
            actor_user_id=actor_user_id,
            action="compound_rules_evaluated",
            target_entity_type="plant",
            target_entity_id=plant_id,
            after_state={"fired_rule_ids": [finding.rule_id for finding in findings]},
            commit=True,
        )
        return RuleEvaluationResponse(
            plant_id=plant_id,
            findings=[
                RuleFindingResponse(
                    rule_id=finding.rule_id,
                    name=finding.name,
                    risk_level=finding.risk_level,
                    title=finding.title,
                    message=finding.message,
                    evidence=[
                        EvidenceItem(
                            evidence_type=evidence.evidence_type,
                            record_id=evidence.record_id,
                            role=evidence.role,
                        )
                        for evidence in finding.evidence
                    ],
                )
                for finding in findings
            ],
        )

    @staticmethod
    async def classify(
        session: AsyncSession,
        *,
        payload: RiskClassificationRequest,
        actor_user_id: str,
    ) -> RiskClassificationResponse:
        """Classify a feature vector and persist model provenance."""
        features = RiskFeatures(
            gas=payload.gas,
            temperature=payload.temperature,
            pressure=payload.pressure,
            humidity=payload.humidity,
            worker_count=payload.worker_count,
            maintenance_active=payload.maintenance_active,
            permit_type=payload.permit_type,
        )
        prediction = RiskClassifier().predict(features)
        assessment = RiskAssessment(
            plant_id=payload.plant_id,
            assessed_at=datetime.now(UTC),
            risk_level=prediction.risk_level,
            score=prediction.score,
            rule_ids=[],
            model_name=prediction.model_name,
            model_version=prediction.model_version,
            explanation={"features": payload.model_dump()},
        )
        session.add(assessment)
        await AuditService.record(
            session,
            actor_user_id=actor_user_id,
            action="risk_classified",
            target_entity_type="plant",
            target_entity_id=payload.plant_id,
            after_state={
                "risk_level": prediction.risk_level.value,
                "model_version": prediction.model_version,
            },
        )
        await session.commit()
        return RiskClassificationResponse(
            plant_id=payload.plant_id,
            risk_level=prediction.risk_level,
            score=prediction.score,
            model_name=prediction.model_name,
            model_version=prediction.model_version,
        )

    @staticmethod
    async def predict_trends(session: AsyncSession, *, plant_id: str) -> RiskPredictionResponse:
        """Return thirty-minute trend predictions for key telemetry signals."""
        predictor = TimeSeriesPredictor()
        predictions = []
        for signal, sensor_type in {
            "gas": SensorType.GAS,
            "temperature": SensorType.TEMPERATURE,
            "pressure": SensorType.PRESSURE,
        }.items():
            points = await RiskService._recent_points(
                session,
                plant_id=plant_id,
                sensor_type=sensor_type,
            )
            prediction = predictor.predict(signal, points)
            predictions.append(
                TrendPredictionResponse(
                    signal=prediction.signal,
                    predicted_value=prediction.predicted_value,
                    horizon_minutes=prediction.horizon_minutes,
                    trend=prediction.trend,
                    risk_level=prediction.risk_level,
                    minutes_to_high_risk=prediction.minutes_to_high_risk,
                )
            )
        return RiskPredictionResponse(plant_id=plant_id, predictions=predictions)

    @staticmethod
    async def _recent_points(
        session: AsyncSession,
        *,
        plant_id: str,
        sensor_type: SensorType,
    ) -> list[TrendPoint]:
        """Load recent sensor points for trend forecasting."""
        window_start = datetime.now(UTC) - timedelta(minutes=30)
        result = await session.execute(
            select(SensorReading)
            .join(Sensor, Sensor.id == SensorReading.sensor_id)
            .where(
                SensorReading.plant_id == plant_id,
                Sensor.sensor_type == sensor_type,
                SensorReading.measured_at >= window_start,
            )
            .order_by(desc(SensorReading.measured_at))
            .limit(20)
        )
        readings = list(result.scalars())
        return [
            TrendPoint(measured_at=reading.measured_at, value=float(reading.value))
            for reading in readings
        ]
