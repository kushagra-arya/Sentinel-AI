"""Async SQLAlchemy session management for SentinelAI."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield an async SQLAlchemy session for FastAPI dependencies."""
    async with AsyncSessionLocal() as session:
        yield session
