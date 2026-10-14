from collections.abc import Callable
from datetime import date

from fastapi.testclient import TestClient

from app.services.limits import DailyCap
from tests.conftest import ALLOWED_ORIGIN, FakeOpenAI, make_plan

BODY = {"supermarkets": ["Lidl"], "budget": 50}


def test_eleventh_request_in_a_minute_is_rate_limited(
    client: TestClient, fake_llm: FakeOpenAI
) -> None:
    fake_llm.queue_plan(make_plan(), times=10)

    statuses = [client.post("/generate", json=BODY).status_code for _ in range(10)]
    eleventh = client.post("/generate", json=BODY, headers={"Origin": ALLOWED_ORIGIN})

    assert statuses == [200] * 10
    assert eleventh.status_code == 429
    assert eleventh.json() == {"detail": "Too many requests, please try again later"}
    # The browser can read the 429 (CORS header present) and the LLM was not called.
    assert eleventh.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert fake_llm.calls == 10


def test_rate_limit_comes_from_settings(
    make_client: Callable[..., TestClient], fake_llm: FakeOpenAI
) -> None:
    client = make_client(rate_limit="2/minute")
    fake_llm.queue_plan(make_plan(), times=2)

    statuses = [client.post("/generate", json=BODY).status_code for _ in range(3)]

    assert statuses == [200, 200, 429]


def test_health_is_not_rate_limited(client: TestClient) -> None:
    statuses = {client.get("/health").status_code for _ in range(15)}

    assert statuses == {200}


def test_daily_cap_returns_503_once_reached(
    make_client: Callable[..., TestClient], fake_llm: FakeOpenAI
) -> None:
    client = make_client(daily_generate_cap=2)
    fake_llm.queue_plan(make_plan(), times=2)

    responses = [client.post("/generate", json=BODY) for _ in range(3)]

    assert [r.status_code for r in responses] == [200, 200, 503]
    assert responses[2].json() == {"detail": "Daily limit reached, try tomorrow"}
    assert fake_llm.calls == 2


def test_invalid_requests_do_not_use_the_daily_cap(
    make_client: Callable[..., TestClient], fake_llm: FakeOpenAI
) -> None:
    client = make_client(daily_generate_cap=1)
    fake_llm.queue_plan(make_plan())

    assert client.post("/generate", json={"supermarkets": [], "budget": 50}).status_code == 422
    assert client.post("/generate", json=BODY).status_code == 200


def test_daily_cap_resets_on_a_new_utc_day() -> None:
    today = [date(2026, 10, 14)]
    cap = DailyCap(2, today=lambda: today[0])

    assert [cap.try_acquire() for _ in range(3)] == [True, True, False]

    today[0] = date(2026, 10, 15)
    assert cap.try_acquire() is True
