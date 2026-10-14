import asyncio
import json
import os
import socket
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import AsyncOpenAI

# Importing app.main builds the module-level app, which needs a key. Set a fake one so the
# developer's real key from backend/.env is never picked up (env vars win over .env).
os.environ["OPENAI_API_KEY"] = "sk-test-not-a-real-key"

from app.api.deps import get_llm_client  # noqa: E402
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.limits import limiter  # noqa: E402

ALLOWED_ORIGIN = "http://localhost:3000"
FIXTURE_CATALOG = Path(__file__).parent / "fixtures" / "catalog_small.json"
FAKE_BASE_URL = "https://openai.test/v1"

MEAL = {"name": "Oatmeal", "description": "With apples", "calories": 350}
ITEM = {
    "product": "Milk",
    "quantity": "1L",
    "store": "Lidl",
    "approx_price": 1.29,
    "category": "dairy",
    "calories": 640,
    "protein": 34.0,
    "fat": 35.0,
    "carbs": 48.0,
}


def day(name: str) -> dict[str, Any]:
    return {"day": name, "breakfast": MEAL, "lunch": MEAL, "dinner": MEAL, "snack": MEAL}


def make_plan(days: int | None = None, **overrides: Any) -> dict[str, Any]:
    """A schema-valid LLMPlan payload; `days` adds a menu with that many days."""
    plan: dict[str, Any] = {
        "items": [ITEM],
        "total_cost": 1.29,
        "notes": "Buy seasonal.",
        "menu": [day(f"Day {i + 1}") for i in range(days)] if days else None,
    }
    return {**plan, **overrides}


def completion(
    content: str | None, *, refusal: str | None = None, finish_reason: str = "stop"
) -> dict[str, Any]:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 0,
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "finish_reason": finish_reason,
                "message": {"role": "assistant", "content": content, "refusal": refusal},
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


class FakeOpenAI:
    """A real `AsyncOpenAI` whose HTTP transport is scripted: no network, real SDK parsing.

    Queue one reply per expected API call; an unexpected extra call fails the test.
    """

    def __init__(self) -> None:
        self._replies: list[httpx.Response | Exception] = []
        self.requests: list[dict[str, Any]] = []
        self.delay_s = 0.0  # simulated latency of every call
        self.client = AsyncOpenAI(
            api_key="sk-test-not-a-real-key",
            base_url=FAKE_BASE_URL,
            max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(self._handle)),
        )

    async def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        await asyncio.sleep(self.delay_s)
        if not self._replies:
            raise AssertionError("unexpected extra OpenAI call")
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    def queue_plan(self, plan: dict[str, Any], times: int = 1) -> None:
        for _ in range(times):
            self.queue_completion(completion(json.dumps(plan)))

    def queue_completion(self, body: dict[str, Any]) -> None:
        self._replies.append(httpx.Response(200, json=body))

    def queue_raw(self, content: str | None, **kwargs: Any) -> None:
        self.queue_completion(completion(content, **kwargs))

    def queue_status(self, status: int, message: str = "error") -> None:
        self._replies.append(httpx.Response(status, json={"error": {"message": message}}))

    def queue_exception(self, error: Exception) -> None:
        self._replies.append(error)

    @property
    def calls(self) -> int:
        return len(self.requests)

    def messages(self, call: int = -1) -> list[dict[str, Any]]:
        return self.requests[call]["messages"]


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def guard(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("network access attempted in tests")

    monkeypatch.setattr(socket.socket, "connect", guard)


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    # The limiter is module-level (one per process), so clear its counters between tests.
    limiter.reset()


def make_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "openai_api_key": "sk-test-not-a-real-key",
        "openai_model": "test-model",
        "openai_temperature": 0.1,
        "openai_max_tokens": 123,
        "cors_origins": [ALLOWED_ORIGIN],
        "catalog_path": FIXTURE_CATALOG,
        **overrides,
    }
    return Settings(_env_file=None, **values)


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def fake_llm() -> FakeOpenAI:
    return FakeOpenAI()


@pytest.fixture
def make_client(fake_llm: FakeOpenAI) -> Callable[..., TestClient]:
    """Build a TestClient for an app with the given Settings overrides."""

    def build(**overrides: Any) -> TestClient:
        app = create_app(make_settings(**overrides))
        app.dependency_overrides[get_llm_client] = lambda: fake_llm.client
        return TestClient(app)

    return build


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    return make_client()
