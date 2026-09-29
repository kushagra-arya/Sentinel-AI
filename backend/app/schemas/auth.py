"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, Field

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    """Credentials submitted for a token exchange."""

    email: str = Field(
        min_length=3,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="User email address.",
    )
    password: str = Field(min_length=8, max_length=128, description="Plaintext password.")


class TokenPair(BaseModel):
    """Access and refresh tokens issued to an authenticated user."""

    access_token: str = Field(description="Short-lived bearer access token.")
    refresh_token: str = Field(description="Long-lived refresh token.")
    token_type: str = Field(default="bearer", description="OAuth2 token type.")
    expires_in: int = Field(description="Access token lifetime in seconds.")


class RefreshRequest(BaseModel):
    """Refresh-token request payload."""

    refresh_token: str = Field(
        min_length=20,
        max_length=4096,
        description="Valid refresh token to rotate.",
    )


class LogoutRequest(BaseModel):
    """Logout request payload used to revoke a refresh token."""

    refresh_token: str = Field(
        min_length=20,
        max_length=4096,
        description="Refresh token to revoke.",
    )


class UserProfile(BaseModel):
    """Authenticated user profile returned by auth endpoints."""

    id: str = Field(description="User identifier.")
    email: str = Field(description="User email address.")
    full_name: str = Field(description="Display name.")
    role: UserRole = Field(description="Assigned RBAC role.")
    plant_id: str | None = Field(description="Assigned plant identifier, if scoped.")


class AuthenticatedSession(BaseModel):
    """Login response containing tokens and the authenticated user."""

    tokens: TokenPair = Field(description="Issued access and refresh tokens.")
    user: UserProfile = Field(description="Authenticated user profile.")


class LogoutResponse(BaseModel):
    """Logout response after refresh-token revocation."""

    status: str = Field(description="Logout outcome.")
