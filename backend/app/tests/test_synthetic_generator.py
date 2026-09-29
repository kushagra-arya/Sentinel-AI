"""Tests for the synthetic demo dataset generator."""

from __future__ import annotations

from collections.abc import AsyncIterator
import importlib.util
import math
from pathlib import Path
import sys
from types import ModuleType

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.ml.rules_engine import CompoundRuleEngine
from app.models import Base


def load_generator() -> ModuleType:
    """Load the data/synthetic generator module from the repository root."""
    generator_path = Path(__file__).resolve().parents[3] / "data" / "synthetic" / "generator.py"
    spec = importlib.util.spec_from_file_location("sentinelai_synthetic_generator_test", generator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load synthetic generator from {generator_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Create an isolated async SQLite database for synthetic data tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def test_generator_produces_expected_scenarios_and_correlated_readings() -> None:
    """Generated data must contain the planned scenarios and realistic correlations."""
    generator = load_generator()
    dataset = generator.generate_dataset()
    incidents = [scenario for scenario in dataset.scenarios if scenario.kind == "incident"]
    near_misses = [scenario for scenario in dataset.scenarios if scenario.kind == "near_miss"]

    assert len(incidents) == 3
    assert len(near_misses) == 5
    assert len(dataset.readings) > 30_000

    temperatures = _series(dataset.readings, "ZONEC-TEMPERATURE-01")
    pressures = _series(dataset.readings, "ZONEC-PRESSURE-01")
    assert _pearson(temperatures, pressures) > 0.85


@pytest.mark.asyncio
async def test_generated_incidents_trigger_rules_and_near_misses_do_not(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """The generated day must exercise exactly the intended compound-rule outcomes."""
    generator = load_generator()
    dataset = generator.generate_dataset()
    async with session_factory() as session:
        result = await generator.seed_database(session, dataset)
        engine = CompoundRuleEngine()

        for scenario in dataset.scenarios:
            findings = await engine.evaluate(
                session,
                plant_id=result.plant_id,
                evaluated_at=scenario.evaluation_at,
            )
            rule_ids = {finding.rule_id for finding in findings}
            if scenario.expected_to_fire:
                assert scenario.rule_id in rule_ids, scenario.code
                finding = next(finding for finding in findings if finding.rule_id == scenario.rule_id)
                evidence_types = {evidence.evidence_type for evidence in finding.evidence}
                assert "sensor_reading" in evidence_types
                if scenario.rule_id == "gas_increasing_maintenance_workers":
                    assert {"maintenance_activity", "worker_location_event"} <= evidence_types
                if scenario.rule_id == "confined_space_ventilation_failure":
                    assert "permit" in evidence_types
            else:
                assert scenario.rule_id not in rule_ids, scenario.code


def _series(readings: list[dict[str, object]], sensor_external_id: str) -> list[float]:
    """Extract one sensor's numeric reading series."""
    return [
        float(reading["value"])
        for reading in readings
        if reading["sensor_external_id"] == sensor_external_id
    ]


def _pearson(left: list[float], right: list[float]) -> float:
    """Compute a simple Pearson correlation for equal-length numeric vectors."""
    assert len(left) == len(right)
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right, strict=True))
    left_var = math.sqrt(sum((x - left_mean) ** 2 for x in left))
    right_var = math.sqrt(sum((y - right_mean) ** 2 for y in right))
    return numerator / (left_var * right_var)
