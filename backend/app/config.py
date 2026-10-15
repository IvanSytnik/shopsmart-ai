from pathlib import Path
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
    # Output token limit per call, sized to the request: shopping lists are short, a menu
    # grows with its days. A reply cut off at the limit counts as unusable (repair).
    shopping_max_tokens: int = Field(default=1200, gt=0)
    menu_max_tokens_base: int = Field(default=600, gt=0)
    menu_max_tokens_per_day: int = Field(default=450, gt=0)
    # Per OpenAI call. Long menus can take 30 s+; the request deadline still caps the total.
    openai_timeout_s: float = Field(default=40, gt=0)
    openai_max_retries: int = Field(default=0, ge=0)  # SDK retries; the deadline covers all calls
    # Whole /generate budget (first call + repair); keep below the frontend's 70 s timeout.
    request_deadline_s: float = Field(default=55, gt=0)
    # Skip the repair call if less than this is left of the deadline.
    repair_min_remaining_s: float = Field(default=20, ge=0)
    # Menu mode: a plan below this many kcal per person and day is sent back for repair.
    min_kcal_per_person_day: int = Field(default=1600, ge=0)
    # Menu mode: portions above this many kcal per person and day are sent back for repair.
    max_kcal_per_person_day: int = Field(default=3500, ge=1)
    # Below this budget per person and day (EUR), food candidates with the highest cost per
    # 1000 kcal are not offered to the LLM (0 turns the filter off).
    tight_budget_per_person_day: float = Field(default=7.0, ge=0)
    # A plan at most this fraction over budget is trimmed by the server instead of repaired.
    trim_tolerance: float = Field(default=0.10, ge=0)
    # Max enum values in the LLM response schema; above it product ids are sent as plain
    # strings (see app.schemas.llm.build_plan_model). OpenAI's own limit is higher.
    max_schema_enum_values: int = Field(default=500, ge=0)
    catalog_path: Path = Path(__file__).parent / "data" / "catalog.json"
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
