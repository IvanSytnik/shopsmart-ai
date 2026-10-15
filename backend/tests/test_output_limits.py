"""Output size: max_tokens sized to the request, short text required by prompt and schema."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from tests.conftest import BODY, FakeOpenAI, make_plan


@pytest.mark.parametrize(
    ("body", "max_tokens"),
    [
        (BODY, 1200),
        ({**BODY, "mode": "shopping", "days": 3}, 1200),  # days don't matter for a list
        ({**BODY, "mode": "menu", "days": 1}, 1050),  # 600 + 450
        ({**BODY, "mode": "menu", "days": 3}, 1950),
        ({**BODY, "mode": "menu", "days": 7}, 3750),
    ],
    ids=["shopping", "shopping-3-days", "menu-1-day", "menu-3-days", "menu-7-days"],
)
def test_max_tokens_is_sized_to_the_request(
    client: TestClient, fake_llm: FakeOpenAI, body: dict[str, object], max_tokens: int
) -> None:
    days = body.get("days") if body.get("mode") == "menu" else None
    fake_llm.queue_plan(make_plan(days=days if isinstance(days, int) else None))

    response = client.post("/generate", json=body)

    assert response.status_code == 200
    assert fake_llm.requests[0]["max_completion_tokens"] == max_tokens


def test_max_tokens_constants_come_from_settings(
    make_client: Callable[..., TestClient], fake_llm: FakeOpenAI
) -> None:
    client = make_client(menu_max_tokens_base=100, menu_max_tokens_per_day=10)
    fake_llm.queue_plan(make_plan(days=2))

    client.post("/generate", json={**BODY, "mode": "menu", "days": 2})

    assert fake_llm.requests[0]["max_completion_tokens"] == 120


def test_max_tokens_defaults() -> None:
    settings = Settings(_env_file=None, openai_api_key="sk-test")

    assert settings.shopping_max_tokens == 1200
    assert (settings.menu_max_tokens_base, settings.menu_max_tokens_per_day) == (600, 450)


def test_prompt_and_schema_ask_for_short_text(client: TestClient, fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_plan(make_plan(days=1))

    client.post("/generate", json={**BODY, "mode": "menu", "days": 1})

    schema = fake_llm.requests[0]["response_format"]["json_schema"]["schema"]
    meal = schema["$defs"]["LLMMeal"]["properties"]
    assert meal["description"]["description"] == "At most 8 words."
    assert schema["properties"]["notes"]["description"] == "One short sentence of shopping tips."
    system_prompt = fake_llm.messages()[0]["content"]
    assert "a meal description has at most 8 words, `notes` is one sentence" in system_prompt
