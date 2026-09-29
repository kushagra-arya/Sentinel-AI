"""Small in-process rate limiter for security-sensitive API paths.

This limiter is intentionally process-local for the current Docker demo. A
multi-instance deployment should replace the storage with Redis while keeping
the same FastAPI dependency surface.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from typing import Callable

from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings


class InMemoryRateLimiter:
    """Sliding-window request limiter keyed by bucket and client identity."""

    def __init__(self) -> None:
        """Create empty in-memory limiter state."""
        self._events: dict[str, deque[datetime]] = defaultdict(deque)

    def check(self, *, key: str, limit: int, window_seconds: int) -> None:
        """Record one request or raise when the key exceeds its window budget."""
        now = datetime.now(UTC)
        window_start = now - timedelta(seconds=window_seconds)
        events = self._events[key]
        while events and events[0] < window_start:
            events.popleft()
        if len(events) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Retry after the current window.",
                headers={"Retry-After": str(window_seconds)},
            )
        events.append(now)

    def reset(self) -> None:
        """Clear limiter state for tests and process lifecycle resets."""
        self._events.clear()


rate_limiter = InMemoryRateLimiter()


def rate_limit(bucket: str) -> Callable:
    """Return a FastAPI dependency enforcing the configured bucket limit."""

    async def dependency(
        request: Request,
        settings: Settings = Depends(get_settings),
    ) -> None:
        """Apply a sliding-window limit to one request."""
        client_host = request.client.host if request.client else "unknown"
        limit = (
            settings.auth_rate_limit_per_minute
            if bucket == "auth"
            else settings.chat_rate_limit_per_minute
        )
        rate_limiter.check(
            key=f"{bucket}:{client_host}:{request.url.path}",
            limit=limit,
            window_seconds=60,
        )

    return dependency
