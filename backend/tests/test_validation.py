from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import FakeLLMClient

VALID: dict[str, Any] = {"supermarkets": ["Lidl"], "budget": 50}


def payload(**overrides: Any) -> dict[str, Any]:
    return {**VALID, **overrides}


@pytest.mark.parametrize(
    ("case", "body"),
    [
        ("mode not in enum", payload(mode="weekly")),
        ("language not in enum", payload(language="fr")),
        ("supermarkets empty", payload(supermarkets=[])),
        ("supermarkets unknown store", payload(supermarkets=["Billa"])),
        ("supermarkets duplicates", payload(supermarkets=["Lidl", "Lidl"])),
        (
            "supermarkets more than 5",
            payload(supermarkets=["Lidl", "Aldi", "Edeka", "Rewe", "Kaufland", "Lidl"]),
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
    ],
)
def test_invalid_input_is_rejected(
    client: TestClient, fake_llm: FakeLLMClient, case: str, body: dict[str, Any]
) -> None:
    response = client.post("/generate", json=body)

    assert response.status_code == 422, case
    assert fake_llm.completions.calls == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"budget": 10},
        {"budget": 1000},
        {"family_size": 1},
        {"family_size": 10},
        {"mode": "menu", "days": 1},
        {"mode": "menu", "days": 7},
        {"supermarkets": ["Lidl", "Aldi", "Edeka", "Rewe", "Kaufland"]},
        {"preferences": "  " + "a" * 300 + "  "},
    ],
)
def test_boundary_values_are_accepted(
    client: TestClient, fake_llm: FakeLLMClient, overrides: dict[str, Any]
) -> None:
    fake_llm.reply_with({"items": [], "total_cost": 0, "menu": []})

    response = client.post("/generate", json=payload(**overrides))

    assert response.status_code == 200, overrides
