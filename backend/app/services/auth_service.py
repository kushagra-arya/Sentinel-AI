"""Authentication service for JWT login, refresh rotation, and logout."""

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import create_token, decode_token, get_user_by_email, verify_password
from app.models.auth_tokens import RefreshToken
from app.models.users import User
from app.schemas.auth import AuthenticatedSession, TokenPair, UserProfile
from app.services.audit_service import AuditService


class AuthService:
    """Application authentication workflows with refresh-token revocation."""

    @staticmethod
    async def login(
        session: AsyncSession,
        *,
        email: str,
        password: str,
        settings: Settings,
    ) -> AuthenticatedSession:
        """Authenticate a user and issue access and refresh tokens."""
        user = await get_user_by_email(session, email)
        invalid_credentials = (
            user is None
            or not user.is_active
            or not verify_password(password, user.hashed_password)
        )
        if invalid_credentials:
            await AuditService.record(
                session,
                actor_user_id=None,
                action="login_failed",
                target_entity_type="user",
                target_entity_id=email.lower(),
                after_state={"reason": "invalid_credentials"},
                commit=True,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        response, _refresh_jti = await AuthService._issue_token_pair(
            session,
            user=user,
            settings=settings,
        )
        await AuditService.record(
            session,
            actor_user_id=user.id,
            action="login",
            target_entity_type="user",
            target_entity_id=user.id,
            after_state={"email": user.email},
        )
        await session.commit()
        return response

    @staticmethod
    async def refresh(
        session: AsyncSession,
        *,
        refresh_token: str,
        settings: Settings,
    ) -> AuthenticatedSession:
        """Rotate a valid refresh token and return a new token pair."""
        payload = decode_token(refresh_token, settings)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token required.",
            )

        token_jti = payload.get("jti")
        user_id = payload.get("sub")
        if not isinstance(token_jti, str) or not isinstance(user_id, str):
            await AuditService.record(
                session,
                actor_user_id=None,
                action="refresh_failed",
                target_entity_type="refresh_token",
                target_entity_id="invalid",
                after_state={"reason": "malformed_claims"},
                commit=True,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            )

        refresh_record = await AuthService._get_refresh_record(session, token_jti)
        now = datetime.now(UTC)
        if refresh_record is None or refresh_record.revoked_at is not None:
            await AuditService.record(
                session,
                actor_user_id=user_id,
                action="refresh_failed",
                target_entity_type="refresh_token",
                target_entity_id=token_jti,
                after_state={"reason": "revoked_or_missing"},
                commit=True,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token revoked.",
            )
        if AuthService._is_expired(refresh_record.expires_at, now):
            await AuditService.record(
                session,
                actor_user_id=user_id,
                action="refresh_failed",
                target_entity_type="refresh_token",
                target_entity_id=token_jti,
                after_state={"reason": "expired"},
                commit=True,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired.",
            )

        user = await session.get(User, user_id)
        if user is None or not user.is_active:
            await AuditService.record(
                session,
                actor_user_id=user_id,
                action="refresh_failed",
                target_entity_type="user",
                target_entity_id=user_id,
                after_state={"reason": "inactive_or_missing"},
                commit=True,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is inactive.",
            )

        response, replacement_jti = await AuthService._issue_token_pair(
            session,
            user=user,
            settings=settings,
        )
        refresh_record.revoked_at = now
        refresh_record.replaced_by_jti = replacement_jti
        await AuditService.record(
            session,
            actor_user_id=user.id,
            action="refresh_token_rotated",
            target_entity_type="refresh_token",
            target_entity_id=token_jti,
            after_state={"replaced_by_jti": refresh_record.replaced_by_jti},
        )
        await session.commit()
        return response

    @staticmethod
    async def logout(
        session: AsyncSession,
        *,
        refresh_token: str,
        settings: Settings,
        actor_user_id: str,
    ) -> None:
        """Revoke a refresh token during logout."""
        payload = decode_token(refresh_token, settings)
        token_jti = payload.get("jti")
        if not isinstance(token_jti, str):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            )

        refresh_record = await AuthService._get_refresh_record(session, token_jti)
        if refresh_record is not None and refresh_record.revoked_at is None:
            refresh_record.revoked_at = datetime.now(UTC)

        await AuditService.record(
            session,
            actor_user_id=actor_user_id,
            action="logout",
            target_entity_type="refresh_token",
            target_entity_id=token_jti,
        )
        await session.commit()

    @staticmethod
    async def _issue_token_pair(
        session: AsyncSession,
        *,
        user: User,
        settings: Settings,
    ) -> tuple[AuthenticatedSession, str]:
        """Issue and persist a new access and refresh token pair."""
        access_token, _, _ = create_token(
            user.id,
            "access",
            timedelta(minutes=settings.access_token_expire_minutes),
            settings,
            extra_claims={"role": user.role.value, "plant_id": user.plant_id},
        )
        refresh_token, refresh_jti, refresh_expires_at = create_token(
            user.id,
            "refresh",
            timedelta(minutes=settings.refresh_token_expire_minutes),
            settings,
        )
        session.add(
            RefreshToken(
                user_id=user.id,
                token_jti=refresh_jti,
                expires_at=refresh_expires_at,
            )
        )
        token_pair = TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )
        return (
            AuthenticatedSession(
                tokens=token_pair,
                user=UserProfile(
                    id=user.id,
                    email=user.email,
                    full_name=user.full_name,
                    role=user.role,
                    plant_id=user.plant_id,
                ),
            ),
            refresh_jti,
        )

    @staticmethod
    async def _get_refresh_record(session: AsyncSession, token_jti: str) -> RefreshToken | None:
        """Return a refresh-token persistence record by token identifier."""
        result = await session.execute(
            select(RefreshToken).where(RefreshToken.token_jti == token_jti)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _is_expired(expires_at: datetime, now: datetime) -> bool:
        """Compare datetimes defensively across PostgreSQL and SQLite test drivers."""
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at < now
