from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.schemas.requests import GenerateRequest
from tests.conftest import BODY, FakeOpenAI, make_plan

VALID: dict[str, Any] = BODY


def payload(**overrides: Any) -> dict[str, Any]:
    return {**VALID, **overrides}


@pytest.mark.parametrize(
    ("case", "body"),
    [
        ("mode not in enum", payload(mode="weekly")),
        ("language not in enum", payload(language="fr")),
        ("supermarkets empty", payload(supermarkets=[])),
        ("supermarkets empty name", payload(supermarkets=[" "])),
        ("supermarkets name too long", payload(supermarkets=["x" * 41])),
        ("supermarkets duplicates", payload(supermarkets=["Lidl", "Lidl"])),
        (
            "supermarkets more than 5",
            payload(supermarkets=["A", "B", "C", "D", "E", "F"]),
        ),
        ("supermarkets missing", {"budget": 50}),
        ("budget below 10", payload(budget=9.99)),
        ("budget above 1000", payload(budget=1000.01)),
        ("budget missing", {"supermarkets": ["Lidl"]}),
        ("family_size below 1", payload(family_size=0)),
        ("family_size above 10", payload(family_size=11)),
        ("days below 1", payload(mode="menu", days=0)),
        ("days above 7", payload(mode="menu", days=8)),
        ("days null", payload(mode="menu", days=None)),
        ("preferences over 300 chars", payload(preferences="a" * 301)),
        ("diets unknown tag", payload(diets=["keto"])),
        ("diets duplicates", payload(diets=["vegan", "vegan"])),
        ("diets not a list", payload(diets="vegan")),
        ("country not in enum", payload(country="CH")),
    ],
)
def test_invalid_input_is_rejected(
    client: TestClient, fake_llm: FakeOpenAI, case: str, body: dict[str, Any]
) -> None:
    response = client.post("/generate", json=body)

    assert response.status_code == 422, case
    body = response.json()
    assert (body["detail"], body["code"]) == ("Invalid request", "validation_error")
    assert body["errors"] and all(set(e) == {"loc", "msg"} for e in body["errors"])
    assert fake_llm.calls == 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"budget": 10},
        {"budget": 1000},
        {"family_size": 1},
        {"family_size": 10},
        {"mode": "menu", "days": 1},
        {"mode": "menu", "days": 7},
        {"supermarkets": ["Lidl", "Penny"]},
        {"preferences": "  " + "a" * 300 + "  "},
        {"diets": []},
        {"diets": ["vegetarian", "gluten_free"]},
        {"country": "AT"},
    ],
)
def test_boundary_values_are_accepted(
    client: TestClient, fake_llm: FakeOpenAI, overrides: dict[str, Any]
) -> None:
    menu_days = overrides["days"] if overrides.get("mode") == "menu" else None
    fake_llm.queue_plan(make_plan(days=menu_days))

    response = client.post("/generate", json=payload(**overrides))

    assert response.status_code == 200, overrides


def test_diets_and_country_defaults() -> None:
    request = GenerateRequest.model_validate(VALID)

    assert (request.diets, request.country) == ([], "AT")


@pytest.mark.parametrize(
    "overrides",
    [{"diets": ["vegetarian", "vegan", "gluten_free", "lactose_free"]}, {"country": "DE"}],
)
def test_schema_accepts(overrides: dict[str, Any]) -> None:
    # Schema only: the fixture catalog has too few products for all four diets at once.
    GenerateRequest.model_validate(payload(**overrides))
