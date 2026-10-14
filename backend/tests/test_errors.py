from collections.abc import Callable

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


def test_openai_timeout_returns_504(
    client: TestClient, fake_llm: FakeOpenAI, caplog: pytest.LogCaptureFixture
) -> None:
    fake_llm.queue_exception(httpx.ReadTimeout("timed out"))

    response = client.post("/generate", json=BODY)

    assert response.status_code == 504
    assert response.json() == {"detail": "AI service timed out"}
    assert fake_llm.calls == 1
    assert "OpenAI request timed out" in caplog.text


def test_api_error_is_not_retried_by_the_app(client: TestClient, fake_llm: FakeOpenAI) -> None:
    # The test client has SDK max_retries=0, so every call here is an app-level attempt.
    fake_llm.queue_status(500, "upstream exploded")

    response = client.post("/generate", json=BODY)

    assert response.status_code == 503
    assert response.json() == {"detail": "AI service unavailable"}
    assert fake_llm.calls == 1


def test_request_deadline_exceeded_returns_504(
    make_client: Callable[..., TestClient], fake_llm: FakeOpenAI, caplog: pytest.LogCaptureFixture
) -> None:
    client = make_client(request_deadline_s=0.2)
    fake_llm.delay_s = 5
    fake_llm.queue_plan(make_plan())

    response = client.post("/generate", json=BODY)

    assert response.status_code == 504
    assert response.json() == {"detail": "AI service timed out"}
    assert fake_llm.calls == 1
    assert "Request deadline of 0.2s exceeded" in caplog.text


def test_repair_is_skipped_when_too_little_time_is_left(
    make_client: Callable[..., TestClient], fake_llm: FakeOpenAI, caplog: pytest.LogCaptureFixture
) -> None:
    # A slow, unusable first reply leaves < repair_min_remaining_s of the deadline.
    client = make_client(request_deadline_s=1.0, repair_min_remaining_s=0.9)
    fake_llm.delay_s = 0.2
    fake_llm.queue_raw("Sure! Milk, bread, eggs.")

    response = client.post("/generate", json=BODY)

    assert response.status_code == 504
    assert response.json() == {"detail": "AI service timed out"}
    assert fake_llm.calls == 1  # no repair attempt
    assert "Skipping LLM repair attempt" in caplog.text


def test_repair_runs_when_enough_time_is_left(
    make_client: Callable[..., TestClient], fake_llm: FakeOpenAI
) -> None:
    client = make_client(request_deadline_s=5.0, repair_min_remaining_s=1.0)
    fake_llm.delay_s = 0.2
    fake_llm.queue_raw("Sure! Milk, bread, eggs.")
    fake_llm.queue_plan(make_plan())

    response = client.post("/generate", json=BODY)

    assert response.status_code == 200
    assert fake_llm.calls == 2
