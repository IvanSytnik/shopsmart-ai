import json
import os
import socket
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

# Importing app.main builds the module-level app, which needs a key. Set a fake one so the
# developer's real key from backend/.env is never picked up (env vars win over .env).
os.environ["OPENAI_API_KEY"] = "sk-test-not-a-real-key"

from app.api.deps import get_llm_client  # noqa: E402
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

ALLOWED_ORIGIN = "http://localhost:3000"


class FakeCompletions:
    """Stands in for `OpenAI().chat.completions`; records calls, replies with canned content."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.content: str | None = None
        self.error: Exception | None = None

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeLLMClient:
    def __init__(self) -> None:
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)

    def reply_with(self, payload: dict[str, Any], fenced: bool = True) -> None:
        body = json.dumps(payload)
        self.completions.content = f"```json\n{body}\n```" if fenced else body

    def reply_raw(self, content: str | None) -> None:
        self.completions.content = content

    def fail_with(self, error: Exception) -> None:
        self.completions.error = error

    @property
    def last_messages(self) -> tuple[str, str]:
        messages = self.completions.calls[-1]["messages"]
        return messages[0]["content"], messages[1]["content"]


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def guard(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("network access attempted in tests")

    monkeypatch.setattr(socket.socket, "connect", guard)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        openai_api_key="sk-test-not-a-real-key",
        openai_model="test-model",
        openai_temperature=0.1,
        openai_max_tokens=123,
        cors_origins=[ALLOWED_ORIGIN],
    )


@pytest.fixture
def fake_llm() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture
def client(settings: Settings, fake_llm: FakeLLMClient) -> TestClient:
    app = create_app(settings)
    app.dependency_overrides[get_llm_client] = lambda: fake_llm
    return TestClient(app)
