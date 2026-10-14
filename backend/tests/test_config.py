import pytest
from pydantic import ValidationError

from app.config import Settings


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
