"""Validated server configuration; never load another project's credentials."""

from pathlib import Path
from typing import Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HARD_INPUT_LIMIT = 32_000
ModelMode = Literal["fake", "provider"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HEALTH_AGENT_",
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="forbid",
        hide_input_in_errors=True,
        frozen=True,
        allow_inf_nan=False,
    )

    model_mode: ModelMode
    model_name: str | None = None
    model_base_url: AnyHttpUrl | None = Field(default=None, repr=False)
    model_api_key: SecretStr | None = Field(default=None, repr=False)
    request_timeout_seconds: float = Field(default=60, gt=0, le=300)
    model_timeout_seconds: float = Field(default=20, gt=0, le=300)
    model_max_retries: int = Field(default=1, ge=0, le=2)
    max_steps: int = Field(default=12, ge=2, le=100)
    max_input_chars: int = Field(default=8000, ge=1, le=HARD_INPUT_LIMIT)
    local_user_id: str = Field(default="local-user", min_length=1, max_length=64)
    timezone: str = "Asia/Shanghai"
    data_dir: Path = PROJECT_ROOT / "data"
    auth_mode: Literal["local", "token"] = "local"
    api_tokens: dict[str, SecretStr] = Field(default_factory=dict, repr=False)
    max_tool_calls: int = Field(default=12, ge=1, le=100)
    embedding_mode: Literal["local_hash", "provider"] = "local_hash"
    embedding_model: str | None = Field(default=None, min_length=1, max_length=150)
    embedding_dimensions: int = Field(default=1024, ge=128, le=3072)
    memory_enabled: bool = True
    subagents_enabled: bool = True
    max_delegations: int = Field(default=3, ge=1, le=6)
    subagent_max_concurrency: int = Field(default=2, ge=1, le=4)
    subagent_timeout_seconds: float = Field(default=20, gt=0, le=120)
    subagent_max_steps: int = Field(default=8, ge=2, le=50)
    tool_timeout_seconds: float = Field(default=10, gt=0, le=120)
    tool_max_retries: int = Field(default=2, ge=0, le=3)
    tool_retry_initial_delay: float = Field(default=0.1, ge=0, le=5)

    @field_validator("api_tokens")
    @classmethod
    def validate_tokens(cls, value):
        tokens = []
        for user_id, token in value.items():
            if not user_id.strip() or len(user_id) > 64 or len(token.get_secret_value()) < 16:
                raise ValueError(
                    "users and tokens must be valid; tokens require at least 16 characters"
                )
            tokens.append(token.get_secret_value())
        if len(tokens) != len(set(tokens)):
            raise ValueError("tokens must be unique")
        return value

    @field_validator("model_name", "local_user_id")
    @classmethod
    def nonblank_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError):
            raise ValueError("must be a valid IANA timezone") from None
        return value

    @field_validator("model_base_url")
    @classmethod
    def clean_base_url(cls, value: AnyHttpUrl | None) -> AnyHttpUrl | None:
        if value and (value.username or value.password or value.query or value.fragment):
            raise ValueError("base URL must not contain credentials, query or fragment")
        return value

    @model_validator(mode="after")
    def validate_provider_and_budget(self) -> Self:
        if self.embedding_mode == "provider" and (
            not self.embedding_model or not self.model_base_url or not self.model_api_key
        ):
            raise ValueError("provider embeddings require embedding model, base URL and API key")
        if self.auth_mode == "token" and not self.api_tokens:
            raise ValueError("token auth requires API_TOKENS")
        if self.model_timeout_seconds > self.request_timeout_seconds:
            raise ValueError("model timeout must not exceed the total request timeout")
        if self.model_mode == "provider":
            if not self.model_name or not self.model_base_url:
                raise ValueError("provider mode requires MODEL_NAME and MODEL_BASE_URL")
            if not self.model_api_key or not self.model_api_key.get_secret_value().strip():
                raise ValueError("provider mode requires MODEL_API_KEY")
        return self


def load_settings() -> Settings:
    """Give startup a safe error without echoing values from a malformed .env."""
    try:
        return Settings()
    except ValueError:
        raise RuntimeError(
            "Invalid HealthAgent configuration. Check HealthAgent/.env against .env.example."
        ) from None
