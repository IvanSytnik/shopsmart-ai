import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services.llm import FILTERED, REFUSED, SCHEMA_MISMATCH, TRUNCATED
from tests.conftest import BODY, FakeOpenAI, make_plan

SHOPPING = BODY
MENU_3_DAYS = {**BODY, "mode": "menu", "days": 3}


def repair_turn(fake_llm: FakeOpenAI) -> tuple[dict[str, Any], dict[str, Any]]:
    """The (assistant, user) messages appended for the second call."""
    first, second = fake_llm.messages(0), fake_llm.messages(1)
    assert second[: len(first)] == first  # original conversation is kept
    assert len(second) == len(first) + 2
    return second[-2], second[-1]


def test_refusal_is_retried_and_succeeds(
    client: TestClient, fake_llm: FakeOpenAI, caplog: pytest.LogCaptureFixture
) -> None:
    fake_llm.queue_raw(None, refusal="I can't help with that.")
    fake_llm.queue_plan(make_plan())

    response = client.post("/generate", json=SHOPPING)

    assert response.status_code == 200
    assert fake_llm.calls == 2
    assistant, user = repair_turn(fake_llm)
    assert assistant == {"role": "assistant", "content": "I can't help with that."}
    assert user == {"role": "user", "content": REFUSED}
    assert "LLM attempt 1/2 unusable" in caplog.text
    assert "LLM plan accepted on attempt 2/2" in caplog.text


def test_truncated_reply_is_retried(client: TestClient, fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_raw('{"lines": [{"product_id": "at-li', finish_reason="length")
    fake_llm.queue_plan(make_plan())

    response = client.post("/generate", json=SHOPPING)

    assert response.status_code == 200
    assert fake_llm.calls == 2
    assistant, user = repair_turn(fake_llm)
    assert assistant["content"] == "(reply omitted)"  # the truncated JSON isn't echoed back
    assert user["content"] == TRUNCATED


def test_content_filter_is_retried(client: TestClient, fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_raw(None, finish_reason="content_filter")
    fake_llm.queue_plan(make_plan())

    response = client.post("/generate", json=SHOPPING)

    assert response.status_code == 200
    assert repair_turn(fake_llm)[1]["content"] == FILTERED


@pytest.mark.parametrize(
    "reply",
    [
        '{"lines": [{"product_id": "at-lidl-milk-1l"}], "menu": null, "notes": ""}',
        '{"lines": [{"product_id": "made-up-id", "packs": 1}], "menu": null, "notes": ""}',
        '{"lines": [{"product_id": "at-lidl-milk-1l", "packs": 21}], "menu": null, "notes": ""}',
    ],
    ids=["missing-packs", "id-not-a-candidate", "packs-over-20"],
)
def test_schema_mismatch_is_retried(client: TestClient, fake_llm: FakeOpenAI, reply: str) -> None:
    fake_llm.queue_raw(reply)
    fake_llm.queue_plan(make_plan())

    response = client.post("/generate", json=SHOPPING)

    assert response.status_code == 200
    assert repair_turn(fake_llm)[1]["content"] == SCHEMA_MISMATCH


@pytest.mark.parametrize(
    ("first_plan", "expected_problem"),
    [
        (make_plan(days=2), "had 2 days in `menu`, but exactly 3 are required"),
        (make_plan(days=4), "had 4 days in `menu`, but exactly 3 are required"),
        (make_plan(days=None), "had no `menu`. Return a menu with exactly 3 days"),
        ({**make_plan(days=3), "lines": []}, "empty `lines` list"),
    ],
    ids=["menu-too-short", "menu-too-long", "menu-missing", "lines-empty"],
)
def test_business_check_failure_is_retried_with_exact_problem(
    client: TestClient,
    fake_llm: FakeOpenAI,
    first_plan: dict[str, Any],
    expected_problem: str,
) -> None:
    fake_llm.queue_plan(first_plan)
    fake_llm.queue_plan(make_plan(days=3))

    response = client.post("/generate", json=MENU_3_DAYS)

    assert response.status_code == 200
    assert len(response.json()["menu"]) == 3
    assistant, user = repair_turn(fake_llm)
    assert json.loads(assistant["content"]) == first_plan  # the bad reply is echoed back
    assert expected_problem in user["content"]
    if "menu" in expected_problem:
        assert "Monday, Tuesday, Wednesday" in user["content"]


def test_two_unusable_replies_return_502_after_exactly_two_calls(
    client: TestClient, fake_llm: FakeOpenAI, caplog: pytest.LogCaptureFixture
) -> None:
    fake_llm.queue_raw("Sure! Milk, bread, eggs.")
    fake_llm.queue_plan({**make_plan(), "lines": []})

    response = client.post("/generate", json=SHOPPING)

    assert response.status_code == 502
    assert response.json() == {"detail": "Failed to generate plan", "code": "generation_failed"}
    assert fake_llm.calls == 2
    assert "LLM attempt 2/2 unusable" in caplog.text


def test_empty_lines_in_shopping_mode_is_retried(client: TestClient, fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_plan({**make_plan(), "lines": []})
    fake_llm.queue_plan(make_plan())

    response = client.post("/generate", json=SHOPPING)

    assert response.status_code == 200
    assert fake_llm.calls == 2
