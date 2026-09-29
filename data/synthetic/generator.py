"""Deterministic synthetic dataset generator for the SentinelAI live demo.

The dataset covers one refinery operating day with high-frequency sensor
readings, lower-frequency worker-location events, permit records, and
maintenance windows. It deliberately contains three compound-rule incidents
and five near-misses calibrated against ``app.ml.compound_rules.yaml``.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import math
from pathlib import Path
import random
import sys
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
if BACKEND_DIR.exists() and str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models.enums import (  # noqa: E402
    EquipmentStatus,
    MaintenanceStatus,
    PermitStatus,
    SensorStatus,
    SensorType,
)
from app.models.equipment import Equipment  # noqa: E402
from app.models.maintenance import MaintenanceActivity  # noqa: E402
from app.models.permits import Permit  # noqa: E402
from app.models.plants import Plant  # noqa: E402
from app.models.sensor_readings import SensorReading  # noqa: E402
from app.models.sensors import Sensor  # noqa: E402
from app.models.workers import Worker, WorkerLocationEvent  # noqa: E402

DEMO_PLANT_CODE = "DEMO-REFINERY-A"
DEFAULT_SEED = 20260707
DEFAULT_START = datetime(2026, 7, 7, 6, 0, tzinfo=UTC)
DEFAULT_END = datetime(2026, 7, 7, 15, 30, tzinfo=UTC)
SENSOR_INTERVAL_SECONDS = 15

ZONES: dict[str, tuple[float, float]] = {
    "Zone A": (18.0, 34.0),
    "Zone B": (52.0, 41.0),
    "Zone C": (77.0, 27.0),
}

SENSOR_UNITS: dict[SensorType, str] = {
    SensorType.GAS: "ppm",
    SensorType.TEMPERATURE: "deg_c",
    SensorType.PRESSURE: "bar",
    SensorType.HUMIDITY: "percent",
    SensorType.VENTILATION: "percent",
}


@dataclass(frozen=True)
class Scenario:
    """One designed incident or near-miss in the generated demo day."""

    code: str
    title: str
    kind: str
    rule_id: str
    zone: str
    starts_at: datetime
    evaluation_at: datetime
    ends_at: datetime
    expected_to_fire: bool
    notes: str


@dataclass
class SyntheticDataset:
    """Generated rows and scenario metadata before database insertion."""

    seed: int
    plant: dict[str, Any]
    equipment: list[dict[str, Any]]
    sensors: list[dict[str, Any]]
    workers: list[dict[str, Any]]
    readings: list[dict[str, Any]]
    worker_locations: list[dict[str, Any]]
    permits: list[dict[str, Any]]
    maintenance: list[dict[str, Any]]
    scenarios: list[Scenario]


@dataclass(frozen=True)
class SeedResult:
    """Summary returned after inserting the generated dataset."""

    plant_id: str
    inserted_counts: dict[str, int]
    scenarios: list[Scenario]


def scenario_catalog(start: datetime = DEFAULT_START) -> list[Scenario]:
    """Return the exact incident and near-miss schedule for the demo day."""

    def at(hours: int, minutes: int) -> datetime:
        return start.replace(hour=hours, minute=minutes, second=0, microsecond=0)

    return [
        Scenario(
            code="INC-001",
            title="Gas rise during active pump maintenance with workers nearby",
            kind="incident",
            rule_id="gas_increasing_maintenance_workers",
            zone="Zone A",
            starts_at=at(8, 29),
            evaluation_at=at(8, 44),
            ends_at=at(9, 6),
            expected_to_fire=True,
            notes="Exercises gas trend + active maintenance + worker proximity.",
        ),
        Scenario(
            code="INC-002",
            title="Confined-space vessel entry during ventilation failure",
            kind="incident",
            rule_id="confined_space_ventilation_failure",
            zone="Zone B",
            starts_at=at(10, 20),
            evaluation_at=at(10, 34),
            ends_at=at(11, 15),
            expected_to_fire=True,
            notes="Exercises confined-space permit + ventilation below 30 percent.",
        ),
        Scenario(
            code="INC-003",
            title="Reactor temperature excursion with pressure increase",
            kind="incident",
            rule_id="high_temperature_pressure_increase",
            zone="Zone C",
            starts_at=at(13, 10),
            evaluation_at=at(13, 25),
            ends_at=at(13, 55),
            expected_to_fire=True,
            notes="Exercises high temperature + pressure rise in the same zone.",
        ),
        Scenario(
            code="NM-001",
            title="Small gas rise during maintenance with workers present",
            kind="near_miss",
            rule_id="gas_increasing_maintenance_workers",
            zone="Zone A",
            starts_at=at(7, 15),
            evaluation_at=at(7, 30),
            ends_at=at(7, 45),
            expected_to_fire=False,
            notes="All context exists, but gas trend stays just below the 5 ppm rule delta.",
        ),
        Scenario(
            code="NM-002",
            title="Gas rise during maintenance after area cleared",
            kind="near_miss",
            rule_id="gas_increasing_maintenance_workers",
            zone="Zone A",
            starts_at=at(9, 30),
            evaluation_at=at(9, 45),
            ends_at=at(10, 0),
            expected_to_fire=False,
            notes="Gas and maintenance align, but no worker-location evidence appears nearby.",
        ),
        Scenario(
            code="NM-003",
            title="Confined-space work with low but acceptable ventilation",
            kind="near_miss",
            rule_id="confined_space_ventilation_failure",
            zone="Zone B",
            starts_at=at(11, 20),
            evaluation_at=at(11, 35),
            ends_at=at(12, 0),
            expected_to_fire=False,
            notes="Confined-space permit is active, but ventilation bottoms out just above 30 percent.",
        ),
        Scenario(
            code="NM-004",
            title="Ventilation failure without confined-space entry",
            kind="near_miss",
            rule_id="confined_space_ventilation_failure",
            zone="Zone B",
            starts_at=at(12, 15),
            evaluation_at=at(12, 30),
            ends_at=at(12, 50),
            expected_to_fire=False,
            notes="Ventilation crosses the failure threshold, but no confined-space permit is active.",
        ),
        Scenario(
            code="NM-005",
            title="High reactor temperature with pressure controlled below rule delta",
            kind="near_miss",
            rule_id="high_temperature_pressure_increase",
            zone="Zone C",
            starts_at=at(14, 25),
            evaluation_at=at(14, 40),
            ends_at=at(15, 0),
            expected_to_fire=False,
            notes="Temperature exceeds threshold, but pressure trend remains below the 8 bar delta.",
        ),
    ]


def generate_dataset(
    *,
    seed: int = DEFAULT_SEED,
    start: datetime = DEFAULT_START,
    end: datetime = DEFAULT_END,
) -> SyntheticDataset:
    """Generate deterministic SentinelAI demo rows without writing a database."""

    rng = random.Random(seed)
    scenarios = scenario_catalog(start)
    sensors = _sensor_definitions()
    equipment = _equipment_definitions()
    workers = _worker_definitions()
    return SyntheticDataset(
        seed=seed,
        plant={
            "name": "SentinelAI Demo Refinery",
            "code": DEMO_PLANT_CODE,
            "timezone": "UTC",
            "description": "Synthetic industrial site used for deterministic safety demos.",
        },
        equipment=equipment,
        sensors=sensors,
        workers=workers,
        readings=_generate_readings(rng, sensors, scenarios, start, end),
        worker_locations=_generate_worker_locations(workers, scenarios, start, end),
        permits=_generate_permits(scenarios),
        maintenance=_generate_maintenance(scenarios),
        scenarios=scenarios,
    )


async def seed_database(session: AsyncSession, dataset: SyntheticDataset) -> SeedResult:
    """Idempotently replace the demo plant data with the generated dataset."""

    existing_plant_id = (
        await session.execute(select(Plant.id).where(Plant.code == DEMO_PLANT_CODE))
    ).scalar_one_or_none()
    if existing_plant_id is not None:
        for model in (
            SensorReading,
            WorkerLocationEvent,
            MaintenanceActivity,
            Permit,
            Sensor,
            Equipment,
            Worker,
        ):
            await session.execute(delete(model).where(model.plant_id == existing_plant_id))
        await session.execute(delete(Plant).where(Plant.id == existing_plant_id))
    await session.flush()

    plant = Plant(**dataset.plant)
    session.add(plant)
    await session.flush()

    equipment_by_tag: dict[str, Equipment] = {}
    for row in dataset.equipment:
        equipment = Equipment(plant_id=plant.id, **row)
        session.add(equipment)
        equipment_by_tag[row["asset_tag"]] = equipment
    await session.flush()

    sensor_by_external_id: dict[str, Sensor] = {}
    for row in dataset.sensors:
        sensor = Sensor(
            plant_id=plant.id,
            equipment_id=equipment_by_tag[row["asset_tag"]].id,
            external_id=row["external_id"],
            name=row["name"],
            sensor_type=row["sensor_type"],
            unit=row["unit"],
            zone=row["zone"],
            x_coordinate=row["x_coordinate"],
            y_coordinate=row["y_coordinate"],
            status=SensorStatus.ACTIVE,
        )
        session.add(sensor)
        sensor_by_external_id[row["external_id"]] = sensor
    await session.flush()

    worker_by_badge: dict[str, Worker] = {}
    for row in dataset.workers:
        worker = Worker(plant_id=plant.id, **row)
        session.add(worker)
        worker_by_badge[row["badge_id"]] = worker
    await session.flush()

    permit_by_number: dict[str, Permit] = {}
    for row in dataset.permits:
        permit = Permit(plant_id=plant.id, **row)
        session.add(permit)
        permit_by_number[row["permit_number"]] = permit
    await session.flush()

    for row in dataset.maintenance:
        equipment = equipment_by_tag[row["asset_tag"]]
        permit_id = None
        if row.get("permit_number") is not None:
            permit_id = permit_by_number[row["permit_number"]].id
        session.add(
            MaintenanceActivity(
                plant_id=plant.id,
                equipment_id=equipment.id,
                permit_id=permit_id,
                work_order=row["work_order"],
                maintenance_type=row["maintenance_type"],
                zone=row["zone"],
                status=row["status"],
                starts_at=row["starts_at"],
                ends_at=row["ends_at"],
                description=row["description"],
            )
        )

    for row in dataset.worker_locations:
        session.add(
            WorkerLocationEvent(
                plant_id=plant.id,
                worker_id=worker_by_badge[row["badge_id"]].id,
                zone=row["zone"],
                x_coordinate=row["x_coordinate"],
                y_coordinate=row["y_coordinate"],
                observed_at=row["observed_at"],
            )
        )

    for row in dataset.readings:
        session.add(
            SensorReading(
                plant_id=plant.id,
                sensor_id=sensor_by_external_id[row["sensor_external_id"]].id,
                measured_at=row["measured_at"],
                value=row["value"],
                quality=row["quality"],
            )
        )

    await session.commit()
    return SeedResult(
        plant_id=plant.id,
        inserted_counts={
            "equipment": len(dataset.equipment),
            "sensors": len(dataset.sensors),
            "workers": len(dataset.workers),
            "sensor_readings": len(dataset.readings),
            "worker_locations": len(dataset.worker_locations),
            "permits": len(dataset.permits),
            "maintenance": len(dataset.maintenance),
        },
        scenarios=dataset.scenarios,
    )


def write_csv(dataset: SyntheticDataset, output_dir: Path) -> None:
    """Write generated rows to CSV files for manual inspection and demos."""

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_dict_csv(output_dir / "sensors.csv", dataset.sensors)
    _write_dict_csv(output_dir / "equipment.csv", dataset.equipment)
    _write_dict_csv(output_dir / "workers.csv", dataset.workers)
    _write_dict_csv(output_dir / "sensor_readings.csv", dataset.readings)
    _write_dict_csv(output_dir / "worker_locations.csv", dataset.worker_locations)
    _write_dict_csv(output_dir / "permits.csv", dataset.permits)
    _write_dict_csv(output_dir / "maintenance.csv", dataset.maintenance)
    _write_dict_csv(
        output_dir / "scenarios.csv",
        [
            {
                "code": scenario.code,
                "kind": scenario.kind,
                "rule_id": scenario.rule_id,
                "zone": scenario.zone,
                "starts_at": scenario.starts_at.isoformat(),
                "evaluation_at": scenario.evaluation_at.isoformat(),
                "ends_at": scenario.ends_at.isoformat(),
                "expected_to_fire": scenario.expected_to_fire,
                "notes": scenario.notes,
            }
            for scenario in dataset.scenarios
        ],
    )


def _equipment_definitions() -> list[dict[str, Any]]:
    """Return stable demo equipment rows for the plant zones."""

    return [
        {
            "asset_tag": "P-101",
            "name": "Feed Transfer Pump",
            "equipment_type": "centrifugal_pump",
            "zone": "Zone A",
            "status": EquipmentStatus.ACTIVE,
        },
        {
            "asset_tag": "V-204",
            "name": "Confined Space Vessel",
            "equipment_type": "process_vessel",
            "zone": "Zone B",
            "status": EquipmentStatus.ACTIVE,
        },
        {
            "asset_tag": "R-310",
            "name": "Thermal Reactor",
            "equipment_type": "reactor",
            "zone": "Zone C",
            "status": EquipmentStatus.ACTIVE,
        },
    ]


def _sensor_definitions() -> list[dict[str, Any]]:
    """Return one sensor of each supported type in each process zone."""

    rows: list[dict[str, Any]] = []
    asset_by_zone = {"Zone A": "P-101", "Zone B": "V-204", "Zone C": "R-310"}
    offsets = {
        SensorType.GAS: (-1.2, 1.0),
        SensorType.TEMPERATURE: (1.4, -0.8),
        SensorType.PRESSURE: (0.9, 1.3),
        SensorType.HUMIDITY: (-1.0, -1.1),
        SensorType.VENTILATION: (1.8, 0.4),
    }
    for zone, (x_coord, y_coord) in ZONES.items():
        for sensor_type in SensorType:
            dx, dy = offsets[sensor_type]
            rows.append(
                {
                    "external_id": f"{zone.replace(' ', '').upper()}-{sensor_type.value.upper()}-01",
                    "name": f"{zone} {sensor_type.value.title()} Sensor",
                    "sensor_type": sensor_type,
                    "unit": SENSOR_UNITS[sensor_type],
                    "zone": zone,
                    "asset_tag": asset_by_zone[zone],
                    "x_coordinate": x_coord + dx,
                    "y_coordinate": y_coord + dy,
                }
            )
    return rows


def _worker_definitions() -> list[dict[str, Any]]:
    """Return stable worker identities with day and swing-shift patterns."""

    roles = [
        "operator",
        "operator",
        "mechanical_technician",
        "electrical_technician",
        "safety_watch",
        "supervisor",
        "operator",
        "operator",
        "maintenance_planner",
        "instrument_technician",
        "fire_watch",
        "area_supervisor",
    ]
    return [
        {
            "badge_id": f"WKR-{index:03d}",
            "full_name": f"Demo Worker {index:03d}",
            "role": role,
            "is_active": True,
        }
        for index, role in enumerate(roles, start=1)
    ]


def _generate_readings(
    rng: random.Random,
    sensors: list[dict[str, Any]],
    scenarios: list[Scenario],
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    """Generate correlated high-frequency sensor readings for all zones."""

    readings: list[dict[str, Any]] = []
    timestamp = start
    while timestamp <= end:
        hours = (timestamp - start).total_seconds() / 3600.0
        load = 0.5 + 0.5 * math.sin((hours - 1.5) / 8.5 * math.pi)
        for sensor in sensors:
            zone = sensor["zone"]
            sensor_type = sensor["sensor_type"]
            value = _normal_value(rng, sensor_type, zone, timestamp, load)
            value += _scenario_adjustment(sensor_type, zone, timestamp, scenarios)
            readings.append(
                {
                    "sensor_external_id": sensor["external_id"],
                    "measured_at": timestamp,
                    "value": round(max(value, 0.0), 4),
                    "quality": "good",
                }
            )
        timestamp += timedelta(seconds=SENSOR_INTERVAL_SECONDS)
    return readings


def _normal_value(
    rng: random.Random,
    sensor_type: SensorType,
    zone: str,
    timestamp: datetime,
    load: float,
) -> float:
    """Return a realistic baseline value with mild noise and correlations."""

    zone_offset = {"Zone A": 0.0, "Zone B": 1.3, "Zone C": 2.6}[zone]
    hour = timestamp.hour + timestamp.minute / 60.0
    diurnal = math.sin((hour - 6.0) / 24.0 * 2.0 * math.pi)
    temp_base = 42.0 + zone_offset + 9.0 * load + 2.2 * diurnal + rng.gauss(0.0, 0.12)
    pressure_base = 83.0 + (temp_base - 45.0) * 0.42 + 4.3 * load + rng.gauss(0.0, 0.08)
    if sensor_type == SensorType.TEMPERATURE:
        return temp_base
    if sensor_type == SensorType.PRESSURE:
        return pressure_base
    if sensor_type == SensorType.GAS:
        return 9.0 + 0.7 * load + zone_offset * 0.25 + rng.gauss(0.0, 0.08)
    if sensor_type == SensorType.HUMIDITY:
        return 58.0 - (temp_base - 45.0) * 0.38 + rng.gauss(0.0, 0.25)
    if sensor_type == SensorType.VENTILATION:
        return 78.0 - 3.5 * load + rng.gauss(0.0, 0.18)
    raise ValueError(f"Unsupported sensor type: {sensor_type}")


def _scenario_adjustment(
    sensor_type: SensorType,
    zone: str,
    timestamp: datetime,
    scenarios: list[Scenario],
) -> float:
    """Return the process deviation created by matching scenarios."""

    adjustment = 0.0
    for scenario in scenarios:
        if scenario.zone != zone:
            continue
        if scenario.rule_id == "gas_increasing_maintenance_workers" and sensor_type == SensorType.GAS:
            amplitude = 9.2 if scenario.expected_to_fire else 4.35
            if scenario.code == "NM-002":
                amplitude = 6.4
            adjustment += _ramp_with_decay(timestamp, scenario, amplitude)
        elif scenario.rule_id == "confined_space_ventilation_failure" and sensor_type == SensorType.VENTILATION:
            amplitude = -49.0 if scenario.expected_to_fire or scenario.code == "NM-004" else -43.0
            adjustment += _ramp_with_decay(timestamp, scenario, amplitude)
        elif scenario.rule_id == "high_temperature_pressure_increase":
            if sensor_type == SensorType.TEMPERATURE:
                adjustment += _ramp_with_decay(timestamp, scenario, 30.0 if scenario.expected_to_fire else 26.0)
            elif sensor_type == SensorType.PRESSURE:
                adjustment += _ramp_with_decay(timestamp, scenario, 11.8 if scenario.expected_to_fire else 5.6)
    return adjustment


def _ramp_with_decay(timestamp: datetime, scenario: Scenario, amplitude: float) -> float:
    """Return a linear scenario ramp followed by controlled recovery."""

    if scenario.starts_at <= timestamp <= scenario.evaluation_at:
        span = max((scenario.evaluation_at - scenario.starts_at).total_seconds(), 1.0)
        return amplitude * (timestamp - scenario.starts_at).total_seconds() / span
    if scenario.evaluation_at < timestamp <= scenario.ends_at:
        span = max((scenario.ends_at - scenario.evaluation_at).total_seconds(), 1.0)
        remaining = 1.0 - (timestamp - scenario.evaluation_at).total_seconds() / span
        return amplitude * max(remaining, 0.0)
    return 0.0


def _generate_worker_locations(
    workers: list[dict[str, Any]],
    scenarios: list[Scenario],
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    """Generate event-driven worker location updates with shift patterns."""

    rows: list[dict[str, Any]] = []
    timestamp = start
    control_points = [("Control Room", 8.0, 12.0), ("Workshop", 13.0, 18.0)]
    while timestamp <= end:
        hour = timestamp.hour + timestamp.minute / 60.0
        active_count = 8 if hour < 14.0 else 10
        for index, worker in enumerate(workers[:active_count]):
            location = control_points[index % len(control_points)]
            rows.append(
                {
                    "badge_id": worker["badge_id"],
                    "zone": location[0],
                    "x_coordinate": location[1] + (index % 3),
                    "y_coordinate": location[2] + (index % 2),
                    "observed_at": timestamp,
                }
            )
        timestamp += timedelta(minutes=30)

    scenario_worker_badges = ["WKR-001", "WKR-003"]
    for scenario in scenarios:
        if scenario.rule_id != "gas_increasing_maintenance_workers":
            continue
        if scenario.code == "NM-002":
            continue
        for offset, badge_id in enumerate(scenario_worker_badges):
            x_coord, y_coord = ZONES[scenario.zone]
            rows.append(
                {
                    "badge_id": badge_id,
                    "zone": scenario.zone,
                    "x_coordinate": x_coord + 1.2 + offset,
                    "y_coordinate": y_coord - 0.6 + offset,
                    "observed_at": scenario.evaluation_at - timedelta(minutes=4 - offset),
                }
            )
    return rows


def _generate_permits(scenarios: list[Scenario]) -> list[dict[str, Any]]:
    """Generate permit records only where operationally required."""

    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        if scenario.rule_id == "confined_space_ventilation_failure" and scenario.code != "NM-004":
            rows.append(
                {
                    "permit_number": f"PTW-{scenario.code}",
                    "permit_type": "confined_space",
                    "zone": scenario.zone,
                    "status": PermitStatus.ACTIVE,
                    "starts_at": scenario.starts_at,
                    "expires_at": scenario.ends_at,
                    "description": scenario.title,
                }
            )
        elif scenario.rule_id == "gas_increasing_maintenance_workers":
            rows.append(
                {
                    "permit_number": f"PTW-{scenario.code}",
                    "permit_type": "cold_work",
                    "zone": scenario.zone,
                    "status": PermitStatus.ACTIVE,
                    "starts_at": scenario.starts_at - timedelta(minutes=5),
                    "expires_at": scenario.ends_at,
                    "description": scenario.title,
                }
            )
    return rows


def _generate_maintenance(scenarios: list[Scenario]) -> list[dict[str, Any]]:
    """Generate event-driven maintenance windows for gas-compound scenarios."""

    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        if scenario.rule_id != "gas_increasing_maintenance_workers":
            continue
        rows.append(
            {
                "work_order": f"WO-{scenario.code}",
                "maintenance_type": "pump_seal_inspection",
                "zone": scenario.zone,
                "status": MaintenanceStatus.ACTIVE,
                "starts_at": scenario.starts_at - timedelta(minutes=5),
                "ends_at": scenario.ends_at,
                "description": scenario.title,
                "asset_tag": "P-101",
                "permit_number": f"PTW-{scenario.code}",
            }
        )
    return rows


def _write_dict_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write dictionaries to a CSV file with stable headers."""

    if not rows:
        path.write_text("", encoding="utf-8")
        return
    headers = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in headers})


def _csv_value(value: Any) -> Any:
    """Convert Python objects to readable CSV scalar values."""

    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


async def _seed_from_cli() -> None:
    """Seed the configured application database from the command line."""

    from app.core.database import AsyncSessionLocal

    dataset = generate_dataset()
    async with AsyncSessionLocal() as session:
        await seed_database(session, dataset)


def main() -> None:
    """Run the generator as a CLI for CSV export or database seeding."""

    parser = argparse.ArgumentParser(description="Generate SentinelAI synthetic demo data.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output-dir", type=Path, default=ROOT_DIR / "data" / "synthetic" / "generated")
    parser.add_argument("--seed-db", action="store_true")
    args = parser.parse_args()

    dataset = generate_dataset(seed=args.seed)
    if args.seed_db:
        asyncio.run(_seed_from_cli())
    else:
        write_csv(dataset, args.output_dir)


if __name__ == "__main__":
    main()
