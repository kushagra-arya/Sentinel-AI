"""Authentication, JWT, and RBAC dependencies for SentinelAI."""

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.models.audit_logs import AuditLog
from app.models.enums import UserRole
from app.models.users import User

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    """Hash a plaintext password with the configured password hasher."""
    return password_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored password hash."""
    return password_context.verify(password, hashed_password)


def create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    settings: Settings,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, str, datetime]:
    """Create a signed JWT and return token, token identifier, and expiry."""
    expires_at = datetime.now(UTC) + expires_delta
    token_jti = uuid4().hex
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "jti": token_jti,
        "exp": expires_at,
        "iat": datetime.now(UTC),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, token_jti, expires_at


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    """Decode and validate a JWT using configured signing settings."""
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != settings.jwt_algorithm:
            raise JWTError("Unexpected JWT signing algorithm.")
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> User:
    """Resolve the authenticated active user from a bearer access token."""
    payload = decode_token(token, settings)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject is invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user is inactive or missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


class RoleChecker:
    """FastAPI dependency that enforces route-level RBAC declarations."""

    def __init__(self, allowed_roles: Iterable[UserRole]) -> None:
        """Store the set of roles allowed to access a route."""
        self.allowed_roles = set(allowed_roles)

    async def __call__(
        self,
        request: Request,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db_session),
    ) -> User:
        """Return the current user or reject and audit an authorization failure."""
        if current_user.role not in self.allowed_roles:
            audit = AuditLog(
                actor_user_id=current_user.id,
                action="permission_denied",
                target_entity_type="route",
                target_entity_id=f"{request.method} {request.url.path}",
                before_state=None,
                after_state={
                    "required_roles": sorted(role.value for role in self.allowed_roles),
                    "actual_role": current_user.role.value,
                },
                timestamp=datetime.now(UTC),
            )
            session.add(audit)
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role permissions for this operation.",
            )
        return current_user


def require_roles(*roles: UserRole) -> RoleChecker:
    """Declare the roles that may access a FastAPI route."""
    return RoleChecker(roles)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Return an active or inactive user by normalized email address."""
    result = await session.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()
