import httpx
import pytest
from fastapi.testclient import TestClient

from tests.conftest import FakeOpenAI, make_plan

BODY = {"supermarkets": ["Lidl"], "budget": 50}


def test_openai_connection_error_returns_503(
    client: TestClient, fake_llm: FakeOpenAI, caplog: pytest.LogCaptureFixture
) -> None:
    fake_llm.queue_exception(httpx.ConnectError("connection refused"))

    response = client.post("/generate", json=BODY)

    assert response.status_code == 503
    assert response.json() == {"detail": "AI service unavailable"}
    assert "OpenAI request failed" in caplog.text


def test_openai_status_error_does_not_leak_message(
    client: TestClient, fake_llm: FakeOpenAI, caplog: pytest.LogCaptureFixture
) -> None:
    fake_llm.queue_status(401, "Incorrect API key provided: sk-internal-detail")

    response = client.post("/generate", json=BODY)

    assert response.status_code == 503
    assert response.json() == {"detail": "AI service unavailable"}
    assert "sk-internal-detail" not in response.text
    assert "sk-internal-detail" in caplog.text  # the real error is logged server-side


def test_unexpected_error_returns_generic_500(
    client: TestClient,
    fake_llm: FakeOpenAI,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("internal stack detail")

    monkeypatch.setattr("app.api.generate.to_response", boom)
    fake_llm.queue_plan(make_plan())

    response = client.post("/generate", json=BODY)

    assert response.status_code == 500
    assert response.json() == {"detail": "Failed to generate plan"}
    assert "internal stack detail" not in response.text
    assert "internal stack detail" in caplog.text
