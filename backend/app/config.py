from typing import Annotated, Literal

import limits
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration from environment variables (and `.env` in the working dir)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: SecretStr
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 4000
    openai_timeout_s: float = 45
    openai_max_retries: int = 1  # SDK-level retries for transport/5xx errors
    # Comma-separated in the environment: CORS_ORIGINS=http://localhost:3000,https://example.com
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    environment: Literal["development", "production"] = "development"
    # Per client IP on POST /generate, slowapi syntax: "10/minute", "100/hour"
    rate_limit: str = "10/minute"
    # Max /generate calls per UTC day (in-memory, per process)
    daily_generate_cap: int = Field(default=200, ge=1)

    @field_validator("rate_limit")
    @classmethod
    def check_rate_limit(cls, value: str) -> str:
        limits.parse(value)  # raises ValueError on bad syntax
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("cors_origins")
    @classmethod
    def reject_wildcard(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("CORS_ORIGINS must list explicit origins, not '*'")
        return value
