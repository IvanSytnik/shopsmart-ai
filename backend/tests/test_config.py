import pytest
from pydantic import ValidationError

from app.config import Settings
from app.services.llm import create_llm_client


def test_cors_origins_parsed_from_comma_separated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://shopsmart.example")

    settings = Settings(_env_file=None, openai_api_key="sk-test")

    assert settings.cors_origins == ["http://localhost:3000", "https://shopsmart.example"]


def test_cors_wildcard_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "*")

    with pytest.raises(ValidationError):
        Settings(_env_file=None, openai_api_key="sk-test")


def test_api_key_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_api_key_is_not_exposed_in_repr() -> None:
    settings = Settings(_env_file=None, openai_api_key="sk-test-secret")

    assert "sk-test-secret" not in repr(settings)


def test_invalid_rate_limit_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, openai_api_key="sk-test", rate_limit="lots")


def test_daily_cap_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, openai_api_key="sk-test", daily_generate_cap=0)


def test_llm_client_uses_timeout_and_retries_from_settings() -> None:
    settings = Settings(
        _env_file=None, openai_api_key="sk-test", openai_timeout_s=12.5, openai_max_retries=3
    )

    client = create_llm_client(settings)

    assert client.timeout == 12.5
    assert client.max_retries == 3


def test_timeout_and_retry_defaults() -> None:
    settings = Settings(_env_file=None, openai_api_key="sk-test")

    assert (settings.openai_timeout_s, settings.openai_max_retries) == (25, 0)
    assert (settings.request_deadline_s, settings.repair_min_remaining_s) == (55, 20)
    assert (settings.rate_limit, settings.daily_generate_cap) == ("10/minute", 200)
    assert (settings.min_kcal_per_person_day, settings.max_schema_enum_values) == (1600, 500)
