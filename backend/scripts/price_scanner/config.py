"""Paths and settings of the price scanner."""

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND = Path(__file__).resolve().parents[2]
# Cookies, logins and the chosen PLZ from --login. Holds shop sessions: never commit it.
PROFILE_DIR = BACKEND / ".browser_profile"
# One folder per run with page screenshots, and the offers of the last run (--last-run).
RUNS_DIR = BACKEND / ".scanner"
DEFAULT_REVIEW_FILE = BACKEND / "data_src" / "scanner_review.json"
DEFAULT_MIN_CONFIDENCE = 0.85


class ScannerError(Exception):
    """A problem the scanner reports to the user and stops or skips on (no traceback)."""


class ScannerSettings(BaseSettings):
    """OpenAI settings for the scanner, from the environment or backend/.env.

    Separate from the app's: extraction wants temperature 0 and room for long replies.
    """

    model_config = SettingsConfigDict(env_file=BACKEND / ".env", extra="ignore")

    openai_api_key: SecretStr
    scanner_model: str = "gpt-4o-mini"
    scanner_temperature: float = Field(default=0.0, ge=0, le=2)
    # A busy flyer page lists 20-30 offers of about 100 tokens each.
    scanner_max_tokens: int = Field(default=6000, gt=0)
    scanner_timeout_s: float = Field(default=120, gt=0)
    scanner_max_retries: int = Field(default=2, ge=0)
    # OpenAI calls in flight at once.
    scanner_concurrency: int = Field(default=3, ge=1)
