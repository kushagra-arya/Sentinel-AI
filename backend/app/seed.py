"""Seed entrypoint for deterministic SentinelAI demo data."""

import asyncio
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


def _load_synthetic_generator() -> ModuleType:
    """Load the shared synthetic data generator mounted into the backend container."""
    seed_path = Path(__file__).resolve()
    candidates = [
        seed_path.parents[1] / "data" / "synthetic" / "generator.py",
        seed_path.parents[2] / "data" / "synthetic" / "generator.py",
    ]
    generator_path = next((path for path in candidates if path.exists()), candidates[-1])
    spec = importlib.util.spec_from_file_location("sentinelai_synthetic_generator", generator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load synthetic generator from {generator_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


async def main_async() -> None:
    """Generate and insert the deterministic demo dataset."""
    settings = get_settings()
    configure_logging(settings.log_level)
    generator = _load_synthetic_generator()
    dataset = generator.generate_dataset()
    async with AsyncSessionLocal() as session:
        result = await generator.seed_database(session, dataset)
    logger.info(
        "seed_complete",
        extra={
            "environment": settings.environment,
            "plant_id": result.plant_id,
            "counts": result.inserted_counts,
            "scenario_count": len(result.scenarios),
        },
    )


def main() -> None:
    """Run the async seed workflow from ``python -m app.seed``."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
