"""Audit logging service for security and mutating operations."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_logs import AuditLog


class AuditService:
    """Centralized writer for immutable audit log entries."""

    @staticmethod
    async def record(
        session: AsyncSession,
        *,
        actor_user_id: str | None,
        action: str,
        target_entity_type: str,
        target_entity_id: str,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        commit: bool = False,
    ) -> AuditLog:
        """Create an audit log entry and optionally commit it immediately."""
        audit_log = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            before_state=before_state,
            after_state=after_state,
            timestamp=datetime.now(UTC),
        )
        session.add(audit_log)
        if commit:
            await session.commit()
        return audit_log
