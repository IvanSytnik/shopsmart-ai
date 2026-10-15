"""Budget-aware candidates: €/1000 kcal in the prompt, costly food left out when tight."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.schemas.catalog import NON_FOOD_CATEGORIES
from app.schemas.requests import GenerateRequest
from app.services.catalog import load_catalog
from app.services.planner import (
    MIN_FOOD_CANDIDATES,
    budget_per_person_day,
    cost_per_1000_kcal,
    drop_expensive_calories,
)
from tests.conftest import BODY, FIXTURE_CATALOG, MILK, FakeOpenAI, make_plan, make_settings

CATALOG = load_catalog(FIXTURE_CATALOG)
CHICKEN = "at-lidl-chicken-breast-500g"  # €10.89/1000 kcal, the most expensive calories
APPLES = "at-lidl-apples-1kg"  # €3.83/1000 kcal
OATS = "at-lidl-oat-flakes-500g"  # €0.48/1000 kcal, the cheapest
SOAP = "at-lidl-dish-soap-500ml"
TIGHT = make_settings(tight_budget_per_person_day=7.0)


def request(**fields: Any) -> GenerateRequest:
    return GenerateRequest.model_validate({**BODY, **fields})


def candidates(req: GenerateRequest) -> list[Any]:
    return CATALOG.candidates(req.country, req.supermarkets, req.diets)


def food(products: list[Any]) -> list[Any]:
    return [p for p in products if p.category not in NON_FOOD_CATEGORIES]


def test_cost_per_1000_kcal() -> None:
    milk = CATALOG.get(MILK)  # €1.29 for 640 kcal
    soap = CATALOG.get(SOAP)
    assert milk is not None and soap is not None
    assert float(cost_per_1000_kcal(milk) or 0) == pytest.approx(2.0156, abs=1e-4)
    assert cost_per_1000_kcal(soap) is None


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"budget": 50, "family_size": 2}, "3.57"),  # shopping: 7 days
        ({"budget": 50, "family_size": 2, "mode": "menu", "days": 3}, "8.33"),
        ({"budget": 15, "family_size": 1, "mode": "menu", "days": 1}, "15.00"),
    ],
)
def test_budget_per_person_day(fields: dict[str, Any], expected: str) -> None:
    assert str(budget_per_person_day(request(**fields))) == expected


def test_nothing_is_dropped_on_a_normal_budget() -> None:
    req = request(budget=200, family_size=1)  # €28.57 per person per day
    offered = candidates(req)

    assert drop_expensive_calories(offered, req, TIGHT) == (offered, 0)


def test_the_filter_can_be_turned_off() -> None:
    req = request(budget=10)
    off = make_settings(tight_budget_per_person_day=0)

    assert drop_expensive_calories(candidates(req), req, off)[1] == 0


def test_tight_budget_drops_food_above_the_80th_percentile() -> None:
    req = request(budget=50, family_size=2)  # €3.57 per person per day
    offered = candidates(req)

    kept, dropped = drop_expensive_calories(offered, req, TIGHT)

    kept_ids = [p.id for p in kept]
    assert CHICKEN not in kept_ids and APPLES not in kept_ids
    assert OATS in kept_ids and MILK in kept_ids
    assert SOAP in kept_ids  # non-food is never dropped
    assert dropped == len(offered) - len(kept) == 4  # 18 food -> 14
    assert kept_ids == [p.id for p in offered if p.id in kept_ids]  # order kept
    worst_kept = max(cost_per_1000_kcal(p) or 0 for p in food(kept))
    assert all((cost_per_1000_kcal(p) or 99) > worst_kept for p in food(offered) if p not in kept)


def test_tight_budget_never_leaves_fewer_than_the_minimum() -> None:
    req = request(budget=50, family_size=2, diets=["vegan"])  # 14 food candidates
    offered = candidates(req)
    assert len(food(offered)) == 14

    kept, dropped = drop_expensive_calories(offered, req, TIGHT)

    # 80% would leave 11; the 12 cheapest stay.
    assert len(food(kept)) == MIN_FOOD_CANDIDATES
    assert dropped == 2
    cheapest = sorted(food(offered), key=lambda p: cost_per_1000_kcal(p) or 99)
    assert {p.id for p in food(kept)} == {p.id for p in cheapest[:MIN_FOOD_CANDIDATES]}


def test_tight_request_offers_fewer_candidates_and_says_why(
    make_client: Callable[..., TestClient],
    fake_llm: FakeOpenAI,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = make_client(tight_budget_per_person_day=7.0)
    fake_llm.queue_plan(make_plan({MILK: 2, OATS: 1}))  # apples would be left out

    response = client.post("/generate", json={**BODY, "family_size": 2})

    assert response.status_code == 200
    schema = fake_llm.requests[0]["response_format"]["json_schema"]["schema"]
    enum = schema["$defs"]["LLMLine"]["properties"]["product_id"]["enum"]
    assert CHICKEN not in enum and OATS in enum and len(enum) == 16
    system_prompt, user_message = (m["content"] for m in fake_llm.messages())
    assert "\nBudget per person per day: €3.57\n" in user_message
    assert CHICKEN not in user_message
    assert f"\n{OATS} | Oat flakes | 0.5 kg | €0.89 | Lidl | pantry | €0.48/1000 kcal\n" in (
        user_message
    )
    assert "Below €7.00 it is tight" in system_prompt
    assert "left out 4 costly food candidates" in caplog.text
