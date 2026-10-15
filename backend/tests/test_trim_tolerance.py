"""A plan slightly over budget is trimmed by the server; a larger overshoot is repaired."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from tests.conftest import APPLES, BODY, DEFAULT_LINES, FakeOpenAI, make_plan

CHIPS = "at-lidl-potato-chips-175g"  # €1.79
SMALL_OVER = make_plan({**DEFAULT_LINES, CHIPS: 1})  # 8.85 + 1.79 = 10.64, 6.4% over €10


def test_small_overshoot_is_trimmed_without_a_repair(
    client: TestClient, fake_llm: FakeOpenAI, caplog: pytest.LogCaptureFixture
) -> None:
    fake_llm.queue_plan(SMALL_OVER)

    response = client.post("/generate", json={**BODY, "budget": 10})

    assert response.status_code == 200
    assert fake_llm.calls == 1
    body = response.json()
    # Packs are reduced before lines are dropped: apples 2 -> 1.
    assert body["total"] == 8.65 <= body["budget"]
    assert [(t["product_id"], t["to_packs"]) for t in body["trimmed"]] == [(APPLES, 1)]
    assert body["warnings"] == ["budget_trimmed"]
    assert "€0.64 over budget, within tolerance: trimming" in caplog.text


@pytest.mark.parametrize(
    ("tolerance", "calls"),
    [(0.064, 1), (0.063, 2)],  # 10.64 is exactly the limit / one cent over it
    ids=["at-the-limit", "one-cent-over"],
)
def test_tolerance_boundary(
    make_client: Callable[..., TestClient], fake_llm: FakeOpenAI, tolerance: float, calls: int
) -> None:
    client = make_client(trim_tolerance=tolerance)
    fake_llm.queue_plan(SMALL_OVER)
    fake_llm.queue_plan(make_plan())

    response = client.post("/generate", json={**BODY, "budget": 10})

    assert response.status_code == 200
    assert fake_llm.calls == calls
    assert response.json()["total"] <= 10


def test_large_overshoot_is_still_repaired(client: TestClient, fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_plan(make_plan({**DEFAULT_LINES, CHIPS: 2}))  # 12.43, 24% over
    fake_llm.queue_plan(make_plan())

    response = client.post("/generate", json={**BODY, "budget": 10})

    assert response.status_code == 200
    assert fake_llm.calls == 2
    assert "€2.43 over the budget of €10.00" in fake_llm.messages(1)[-1]["content"]
    assert response.json()["trimmed"] == []


def test_small_menu_overshoot_is_trimmed_without_a_repair(
    client: TestClient, fake_llm: FakeOpenAI
) -> None:
    # 6 people, 1 default day: milk 2 (2.58) + apples 3 (5.97) + rice 2 (4.58) = 13.13,
    # 9.4% over €12.
    fake_llm.queue_plan(make_plan(days=1))

    response = client.post(
        "/generate", json={**BODY, "mode": "menu", "days": 1, "family_size": 6, "budget": 12}
    )

    assert response.status_code == 200
    assert fake_llm.calls == 1
    body = response.json()
    assert body["total"] <= 12
    assert body["trimmed"]
    assert len(body["menu"]) == 1
