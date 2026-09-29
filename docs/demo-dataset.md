# SentinelAI Synthetic Demo Dataset

The generator at `data/synthetic/generator.py` creates one deterministic demo operating day for `SentinelAI Demo Refinery` (`DEMO-REFINERY-A`). It is seedable with `20260707` by default and is loaded into PostgreSQL with `make seed`.

Sensor readings are emitted every 15 seconds for gas, temperature, pressure, humidity, and ventilation sensors in Zone A, Zone B, and Zone C. Worker location, permits, and maintenance records are event-driven. Temperature and pressure share a process-load component so they move together under normal operation, while humidity moves inversely with temperature.

## Incident Schedule

| Code | Time UTC | Zone | Rule exercised | Expected |
| --- | --- | --- | --- | --- |
| INC-001 | 2026-07-07 08:44 | Zone A | `gas_increasing_maintenance_workers` | Fires |
| INC-002 | 2026-07-07 10:34 | Zone B | `confined_space_ventilation_failure` | Fires |
| INC-003 | 2026-07-07 13:25 | Zone C | `high_temperature_pressure_increase` | Fires |

## Near-Miss Schedule

| Code | Time UTC | Zone | Rule approached | Why it does not fire |
| --- | --- | --- | --- | --- |
| NM-001 | 2026-07-07 07:30 | Zone A | `gas_increasing_maintenance_workers` | Gas trend remains just below the 5 ppm delta. |
| NM-002 | 2026-07-07 09:45 | Zone A | `gas_increasing_maintenance_workers` | Gas and maintenance align, but no workers are nearby. |
| NM-003 | 2026-07-07 11:35 | Zone B | `confined_space_ventilation_failure` | Confined-space permit is active, but ventilation stays just above 30 percent. |
| NM-004 | 2026-07-07 12:30 | Zone B | `confined_space_ventilation_failure` | Ventilation fails, but no confined-space permit is active. |
| NM-005 | 2026-07-07 14:40 | Zone C | `high_temperature_pressure_increase` | Temperature is high, but pressure rise stays below the 8 bar delta. |

The rest of the day is extended normal operation so the risk engine can demonstrate low baseline risk between designed events.
