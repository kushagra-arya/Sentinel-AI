"""Config-driven compound risk rule engine for SentinelAI.

Rules are loaded from a JSON-compatible YAML file. Each rule is evaluated over
rolling windows, not single-threshold snapshots, and every firing persists the
exact sensor, permit, maintenance, and worker-location records that satisfied
the rule.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerts import Alert, AlertEvidenceLink
from app.models.enums import AlertStatus, MaintenanceStatus, PermitStatus, RiskLevel, SensorType
from app.models.maintenance import MaintenanceActivity
from app.models.permits import Permit
from app.models.risk_assessments import RiskAssessment
from app.models.sensor_readings import SensorReading
from app.models.sensors import Sensor
from app.models.workers import WorkerLocationEvent

DEFAULT_RULES_PATH = Path(__file__).with_name("compound_rules.yaml")


@dataclass(frozen=True)
class EvidenceRef:
    """Reference to one persisted record that contributed to a rule firing."""

    evidence_type: str
    record_id: str
    role: str


@dataclass
class ConditionResult:
    """Evaluation result for one rule condition."""

    matched: bool
    zone: str | None = None
    evidence: list[EvidenceRef] = field(default_factory=list)


@dataclass
class RuleFinding:
    """A compound-rule firing with complete explainability evidence."""

    rule_id: str
    name: str
    risk_level: RiskLevel
    title: str
    message: str
    evidence: list[EvidenceRef]


class CompoundRuleEngine:
    """Evaluate configured compound risk rules over live plant data."""

    def __init__(self, rules_path: Path = DEFAULT_RULES_PATH) -> None:
        """Load rule definitions from a config file."""
        self.rules_path = rules_path
        self.config = self._load_rules(rules_path)

    async def evaluate_and_persist(
        self,
        session: AsyncSession,
        *,
        plant_id: str,
        evaluated_at: datetime | None = None,
    ) -> list[RuleFinding]:
        """Evaluate all rules for a plant and persist alerts for fired rules."""
        findings = await self.evaluate(session, plant_id=plant_id, evaluated_at=evaluated_at)
        for finding in findings:
            await self._persist_finding(session, plant_id=plant_id, finding=finding)
        if findings:
            await session.commit()
        return findings

    async def evaluate(
        self,
        session: AsyncSession,
        *,
        plant_id: str,
        evaluated_at: datetime | None = None,
    ) -> list[RuleFinding]:
        """Evaluate configured rules without writing alerts."""
        now = evaluated_at or datetime.now(UTC)
        findings: list[RuleFinding] = []
        for rule in self.config["rules"]:
            finding = await self._evaluate_rule(session, plant_id=plant_id, rule=rule, now=now)
            if finding is not None:
                findings.append(finding)
        return findings

    async def _evaluate_rule(
        self,
        session: AsyncSession,
        *,
        plant_id: str,
        rule: dict[str, Any],
        now: datetime,
    ) -> RuleFinding | None:
        """Evaluate one configured rule and return a finding when all conditions match."""
        condition_results: dict[str, ConditionResult] = {}
        evidence: list[EvidenceRef] = []

        for condition in rule["conditions"]:
            result = await self._evaluate_condition(
                session,
                plant_id=plant_id,
                condition=condition,
                previous_results=condition_results,
                now=now,
            )
            if not result.matched or not result.evidence:
                return None
            condition_key = condition["type"]
            condition_results[condition_key] = result
            evidence.extend(result.evidence)

        return RuleFinding(
            rule_id=rule["id"],
            name=rule["name"],
            risk_level=RiskLevel(rule["risk_level"]),
            title=rule["title"],
            message=rule["message"],
            evidence=evidence,
        )

    async def _evaluate_condition(
        self,
        session: AsyncSession,
        *,
        plant_id: str,
        condition: dict[str, Any],
        previous_results: dict[str, ConditionResult],
        now: datetime,
    ) -> ConditionResult:
        """Dispatch condition evaluation by DSL condition type."""
        condition_type = condition["type"]
        zone = self._resolve_zone(condition, previous_results)
        if condition_type == "sensor_trend":
            return await self._sensor_trend(session, plant_id, condition, now, zone)
        if condition_type == "sensor_threshold":
            return await self._sensor_threshold(session, plant_id, condition, now, zone)
        if condition_type == "maintenance_active":
            return await self._maintenance_active(session, plant_id, now, zone)
        if condition_type == "workers_nearby":
            return await self._workers_nearby(session, plant_id, condition, now, zone)
        if condition_type == "active_permit":
            return await self._active_permit(session, plant_id, condition, now, zone)
        raise ValueError(f"Unsupported rule condition type: {condition_type}")

    async def _sensor_trend(
        self,
        session: AsyncSession,
        plant_id: str,
        condition: dict[str, Any],
        now: datetime,
        zone: str | None,
    ) -> ConditionResult:
        """Evaluate an increasing/decreasing sensor trend across a rolling window."""
        window_start = now - timedelta(minutes=condition["window_minutes"])
        query = (
            select(SensorReading, Sensor)
            .join(Sensor, Sensor.id == SensorReading.sensor_id)
            .where(
                SensorReading.plant_id == plant_id,
                Sensor.sensor_type == SensorType(condition["sensor_type"]),
                SensorReading.measured_at >= window_start,
                SensorReading.measured_at <= now,
            )
            .order_by(Sensor.zone, SensorReading.measured_at)
        )
        if zone is not None:
            query = query.where(Sensor.zone == zone)
        rows = (await session.execute(query)).all()
        by_zone: dict[str, list[tuple[SensorReading, Sensor]]] = {}
        for reading, sensor in rows:
            by_zone.setdefault(sensor.zone, []).append((reading, sensor))

        for candidate_zone, readings in by_zone.items():
            if len(readings) < 2:
                continue
            first, _first_sensor = readings[0]
            last, _last_sensor = readings[-1]
            delta = float(last.value) - float(first.value)
            direction = condition.get("direction", "increasing")
            min_delta = float(condition["min_delta"])
            matched = delta >= min_delta if direction == "increasing" else delta <= -min_delta
            if matched:
                return ConditionResult(
                    matched=True,
                    zone=candidate_zone,
                    evidence=[
                        EvidenceRef(
                            "sensor_reading",
                            first.id,
                            f"{condition['sensor_type']}_window_start",
                        ),
                        EvidenceRef(
                            "sensor_reading",
                            last.id,
                            f"{condition['sensor_type']}_window_end",
                        ),
                    ],
                )
        return ConditionResult(matched=False)

    async def _sensor_threshold(
        self,
        session: AsyncSession,
        plant_id: str,
        condition: dict[str, Any],
        now: datetime,
        zone: str | None,
    ) -> ConditionResult:
        """Evaluate the latest sensor value against a threshold."""
        window_start = now - timedelta(minutes=condition.get("window_minutes", 15))
        query = (
            select(SensorReading, Sensor)
            .join(Sensor, Sensor.id == SensorReading.sensor_id)
            .where(
                SensorReading.plant_id == plant_id,
                Sensor.sensor_type == SensorType(condition["sensor_type"]),
                SensorReading.measured_at >= window_start,
                SensorReading.measured_at <= now,
            )
            .order_by(Sensor.zone, desc(SensorReading.measured_at))
        )
        if zone is not None:
            query = query.where(Sensor.zone == zone).limit(1)
        rows = (await session.execute(query)).all()
        if not rows:
            return ConditionResult(matched=False)
        threshold = float(condition["threshold"])
        operator = condition["operator"]
        latest_by_zone: dict[str, tuple[SensorReading, Sensor]] = {}
        for reading, sensor in rows:
            latest_by_zone.setdefault(sensor.zone, (reading, sensor))
        for reading, sensor in latest_by_zone.values():
            value = float(reading.value)
            matched = value >= threshold if operator == "gte" else value <= threshold
            if matched:
                return ConditionResult(
                    matched=True,
                    zone=sensor.zone,
                    evidence=[
                        EvidenceRef(
                            "sensor_reading",
                            reading.id,
                            f"{condition['sensor_type']}_threshold",
                        )
                    ],
                )
        return ConditionResult(matched=False)

    async def _maintenance_active(
        self,
        session: AsyncSession,
        plant_id: str,
        now: datetime,
        zone: str | None,
    ) -> ConditionResult:
        """Evaluate whether maintenance is active in a zone."""
        query = select(MaintenanceActivity).where(
            MaintenanceActivity.plant_id == plant_id,
            MaintenanceActivity.status == MaintenanceStatus.ACTIVE,
            MaintenanceActivity.starts_at <= now,
        )
        if zone is not None:
            query = query.where(MaintenanceActivity.zone == zone)
        activity = (await session.execute(query.limit(1))).scalar_one_or_none()
        if activity is None:
            return ConditionResult(matched=False)
        return ConditionResult(
            matched=True,
            zone=activity.zone,
            evidence=[EvidenceRef("maintenance_activity", activity.id, "active_maintenance")],
        )

    async def _workers_nearby(
        self,
        session: AsyncSession,
        plant_id: str,
        condition: dict[str, Any],
        now: datetime,
        zone: str | None,
    ) -> ConditionResult:
        """Evaluate recent worker location events in the target zone."""
        window_start = now - timedelta(minutes=condition["window_minutes"])
        query = select(WorkerLocationEvent).where(
            WorkerLocationEvent.plant_id == plant_id,
            WorkerLocationEvent.observed_at >= window_start,
            WorkerLocationEvent.observed_at <= now,
        )
        if zone is not None:
            query = query.where(WorkerLocationEvent.zone == zone)
        events = (await session.execute(query)).scalars().all()
        if len(events) < int(condition.get("minimum_count", 1)):
            return ConditionResult(matched=False)
        resolved_zone = zone or events[0].zone
        return ConditionResult(
            matched=True,
            zone=resolved_zone,
            evidence=[
                EvidenceRef("worker_location_event", event.id, "worker_nearby")
                for event in events
            ],
        )

    async def _active_permit(
        self,
        session: AsyncSession,
        plant_id: str,
        condition: dict[str, Any],
        now: datetime,
        zone: str | None,
    ) -> ConditionResult:
        """Evaluate active permits in the current rule window."""
        query = select(Permit).where(
            Permit.plant_id == plant_id,
            Permit.status == PermitStatus.ACTIVE,
            Permit.starts_at <= now,
            Permit.expires_at >= now,
            Permit.permit_type == condition["permit_type"],
        )
        if zone is not None:
            query = query.where(Permit.zone == zone)
        permit = (await session.execute(query.limit(1))).scalar_one_or_none()
        if permit is None:
            return ConditionResult(matched=False)
        return ConditionResult(
            matched=True,
            zone=permit.zone,
            evidence=[EvidenceRef("permit", permit.id, f"{condition['permit_type']}_permit")],
        )

    async def _persist_finding(
        self,
        session: AsyncSession,
        *,
        plant_id: str,
        finding: RuleFinding,
    ) -> Alert:
        """Persist an alert, evidence links, and a risk assessment for a finding."""
        now = datetime.now(UTC)
        alert = Alert(
            plant_id=plant_id,
            risk_level=finding.risk_level,
            status=AlertStatus.OPEN,
            title=finding.title,
            message=finding.message,
            source=f"rule:{finding.rule_id}",
            triggered_at=now,
        )
        session.add(alert)
        await session.flush()
        for evidence in finding.evidence:
            session.add(self._to_alert_evidence(alert.id, evidence))
        session.add(
            RiskAssessment(
                plant_id=plant_id,
                alert_id=alert.id,
                assessed_at=now,
                risk_level=finding.risk_level,
                score=self._risk_score(finding.risk_level),
                rule_ids=[finding.rule_id],
                model_name=None,
                model_version=None,
                explanation={
                    "rule_name": finding.name,
                    "evidence": [evidence.__dict__ for evidence in finding.evidence],
                },
            )
        )
        return alert

    @staticmethod
    def _to_alert_evidence(alert_id: str, evidence: EvidenceRef) -> AlertEvidenceLink:
        """Map an evidence reference into an alert evidence ORM object."""
        kwargs: dict[str, Any] = {"alert_id": alert_id, "evidence_role": evidence.role}
        if evidence.evidence_type == "sensor_reading":
            kwargs["sensor_reading_id"] = evidence.record_id
        elif evidence.evidence_type == "permit":
            kwargs["permit_id"] = evidence.record_id
        elif evidence.evidence_type == "maintenance_activity":
            kwargs["maintenance_activity_id"] = evidence.record_id
        elif evidence.evidence_type == "worker_location_event":
            kwargs["worker_location_event_id"] = evidence.record_id
        else:
            raise ValueError(f"Unsupported evidence type: {evidence.evidence_type}")
        return AlertEvidenceLink(**kwargs)

    @staticmethod
    def _resolve_zone(
        condition: dict[str, Any],
        previous_results: dict[str, ConditionResult],
    ) -> str | None:
        """Resolve a condition zone reference to a prior condition result."""
        reference = condition.get("same_zone_as")
        if reference is None:
            return None
        result = previous_results.get(reference)
        return result.zone if result is not None else None

    @staticmethod
    def _risk_score(risk_level: RiskLevel) -> float:
        """Return a conservative numeric score for a rule-fired risk level."""
        return {
            RiskLevel.LOW: 0.2,
            RiskLevel.MEDIUM: 0.5,
            RiskLevel.HIGH: 0.82,
            RiskLevel.CRITICAL: 0.96,
        }[risk_level]

    @staticmethod
    def _load_rules(path: Path) -> dict[str, Any]:
        """Load JSON-compatible YAML rules from disk."""
        return json.loads(path.read_text(encoding="utf-8"))
