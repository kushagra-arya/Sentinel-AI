"""Environment-driven configuration for SentinelAI."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="local", description="Runtime environment name.")
    project_name: str = Field(default="SentinelAI", description="FastAPI project title.")
    api_v1_prefix: str = Field(default="/api/v1", description="Versioned API path prefix.")
    backend_host: str = Field(default="0.0.0.0", description="Backend bind host.")
    backend_port: int = Field(default=8000, description="Backend bind port.")
    log_level: str = Field(default="INFO", description="Structured logging level.")
    secret_key: str = Field(
        default="change-me-in-production",
        description="Secret key used to sign JWT access and refresh tokens.",
    )
    access_token_expire_minutes: int = Field(
        default=15,
        description="Access token lifetime in minutes.",
    )
    refresh_token_expire_minutes: int = Field(
        default=10080,
        description="Refresh token lifetime in minutes.",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm.")
    jwt_issuer: str = Field(default="sentinelai-backend", description="JWT issuer claim.")
    jwt_audience: str = Field(default="sentinelai-api", description="JWT audience claim.")
    auth_rate_limit_per_minute: int = Field(
        default=20,
        ge=1,
        le=300,
        description="Per-client auth endpoint requests allowed per minute.",
    )
    chat_rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        le=600,
        description="Per-client chat endpoint requests allowed per minute.",
    )
    database_url: str = Field(
        default="postgresql+asyncpg://sentinelai:sentinelai_dev_password@postgres:5432/sentinelai",
        description="Async SQLAlchemy database URL.",
    )
    chroma_url: str = Field(default="http://chromadb:8000", description="ChromaDB service URL.")
    chroma_collection: str = Field(
        default="sentinelai_safety_documents",
        description="ChromaDB collection used for safety assistant retrieval.",
    )
    rag_min_confidence: float = Field(
        default=0.12,
        description="Minimum retrieval confidence required before answering.",
    )

    @property
    def sync_database_url(self) -> str:
        """Return a synchronous SQLAlchemy URL for Alembic migrations."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        """Restrict JWT algorithms to symmetric HMAC algorithms used by this app."""
        allowed = {"HS256", "HS384", "HS512"}
        if value not in allowed:
            raise ValueError(f"Unsupported JWT algorithm: {value}")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings for dependency injection."""
    return Settings()
