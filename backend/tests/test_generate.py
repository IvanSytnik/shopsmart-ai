from datetime import datetime

from fastapi.testclient import TestClient

from tests.conftest import APPLES, BODY, MILK, RICE, SOAP, FakeOpenAI, make_plan

# make_plan() default: milk x2 (2.58) + apples x2 (3.98) at Lidl, rice x1 (2.29) at Penny.
DEFAULT_NUTRITION = {"kcal": 5820.0, "protein_g": 144.0, "fat_g": 81.0, "carbs_g": 1156.0}


def test_shopping_happy_path(client: TestClient, fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_plan(make_plan())

    response = client.post("/generate", json={**BODY, "family_size": 3})

    assert response.status_code == 200
    body = response.json()
    assert [(i["product_id"], i["packs"]) for i in body["items"]] == [
        (MILK, 2),
        (APPLES, 2),
        (RICE, 1),
    ]
    assert body["items"][0] == {
        "product_id": MILK,
        "name": "Whole milk 3.5%",
        "names": {"en": "Whole milk 3.5%", "uk": "Молоко 3,5%", "de": "Vollmilch 3,5%"},
        "store": "Lidl",
        "category": "dairy",
        "packs": 2,
        "pack_size": 1.0,
        "unit": "l",
        "portion_unit": "ml",
        "unit_price": 1.29,
        "line_total": 2.58,
        "nutrition": {"kcal": 1280.0, "protein_g": 68.0, "fat_g": 70.0, "carbs_g": 96.0},
    }
    assert body["subtotals_by_store"] == {"Lidl": 6.56, "Penny": 2.29}
    assert (body["total"], body["budget"], body["budget_remaining"]) == (8.85, 50.0, 41.15)
    assert body["nutrition_totals"] == DEFAULT_NUTRITION
    assert body["kcal_per_person_day"] == 277  # 5820 / (3 people x 7 days)
    assert body["trimmed"] == []
    assert body["kcal_basis"] == "purchased"
    assert body["warnings"] == []
    assert body["menu"] is None
    assert body["notes"] == "Buy seasonal."
    assert (body["catalog_version"], body["price_date"]) == ("test-small-2", "2026-10-01")
    assert datetime.fromisoformat(body["generated_at"]).tzinfo is not None

    assert fake_llm.calls == 1
    request = fake_llm.requests[0]
    assert request["model"] == "test-model"
    assert request["temperature"] == 0.1
    assert request["max_completion_tokens"] == 123
    assert request["response_format"]["type"] == "json_schema"
    assert request["response_format"]["json_schema"]["strict"] is True
    assert request["response_format"]["json_schema"]["name"] == "LLMShoppingPlan"

    system_prompt, user_message = (m["content"] for m in fake_llm.messages())
    assert "`packs` is the number of whole packs, 1-20" in system_prompt
    assert "Write meal names, descriptions and `notes` in English" in system_prompt
    assert user_message.startswith(
        "Country: AT\nStores: Lidl, Penny\nBudget: €50.00\nHousehold: 3 people\nDays: 7\n"
        "Budget per person per day: €2.38\nDiets: none\n"
    )
    assert (
        "\nat-lidl-milk-1l | Whole milk 3.5% | 1 l | €1.29 | Lidl | dairy | €2.02/1000 kcal\n"
        in user_message
    )


def test_menu_happy_path(client: TestClient, fake_llm: FakeOpenAI) -> None:
    plan = make_plan(days=3, notes="Gut.")
    plan["menu"] = [
        {**d, "day": n}
        for d, n in zip(plan["menu"], ["Montag", "Dienstag", "Mittwoch"], strict=True)
    ]
    fake_llm.queue_plan(plan)

    response = client.post("/generate", json={**BODY, "language": "de", "mode": "menu", "days": 3})

    assert response.status_code == 200
    body = response.json()
    assert [d["day"] for d in body["menu"]] == ["Montag", "Dienstag", "Mittwoch"]
    assert body["menu"][0]["breakfast"] == plan["menu"][0]["breakfast"]
    assert body["menu"][0]["breakfast"]["ingredients"] == [
        {"product_id": MILK, "amount_per_person": 200},
        {"product_id": APPLES, "amount_per_person": 150},
    ]
    # Per person and day: milk 200 ml, apples 450 g, rice 200 g; x 2 people x 3 days.
    # milk 1200 ml -> 2 x 1 l, apples 2700 g -> 3 x 1 kg, rice 1200 g -> 2 x 1 kg.
    assert [(i["product_id"], i["packs"]) for i in body["items"]] == [
        (MILK, 2),
        (APPLES, 3),
        (RICE, 2),
    ]
    assert body["items"][0]["name"] == "Vollmilch 3,5%"
    assert body["total"] == 13.13  # 2.58 + 5.97 + 4.58
    # Eaten, not purchased: 128 (milk) + 234 (apples) + 700 (rice).
    assert (body["kcal_per_person_day"], body["kcal_basis"]) == (1062, "menu")
    assert body["nutrition_totals"]["kcal"] == 9840  # purchased: 1280 + 1560 + 7000
    assert fake_llm.calls == 1

    system_prompt, user_message = (m["content"] for m in fake_llm.messages())
    assert "in German" in system_prompt
    assert "exactly 3 days, in this order: Montag, Dienstag, Mittwoch" in system_prompt
    assert "\nDays: 3\n" in user_message
    assert (
        "\nat-lidl-milk-1l | Vollmilch 3,5% | 1 l | €1.29 | Lidl | dairy | portion: ml | "
        "64 kcal/100 ml | €2.02/1000 kcal\n" in user_message
    )
    assert "| portion | energy | €/1000 kcal):" in user_message
    assert "dish-soap" not in user_message  # menus use food only


def test_empty_notes_use_localized_fallback(client: TestClient, fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_plan(make_plan(notes="  "))

    response = client.post("/generate", json={**BODY, "language": "uk"})

    assert response.status_code == 200
    assert response.json()["notes"] == "Список оптимізовано під ваш бюджет."


def test_non_food_item_has_no_nutrition(client: TestClient, fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_plan(make_plan({SOAP: 2, MILK: 1}))

    response = client.post("/generate", json=BODY)

    assert response.status_code == 200
    soap, milk = response.json()["items"]
    assert (soap["product_id"], soap["nutrition"], soap["line_total"]) == (SOAP, None, 1.98)
    assert response.json()["nutrition_totals"]["kcal"] == milk["nutrition"]["kcal"] == 640


def test_menu_from_llm_is_ignored_in_shopping_mode(
    client: TestClient, fake_llm: FakeOpenAI
) -> None:
    fake_llm.queue_plan({**make_plan(), "menu": make_plan(days=2)["menu"]})

    response = client.post("/generate", json={**BODY, "mode": "shopping", "days": 2})

    assert response.status_code == 200
    assert response.json()["menu"] is None
    assert "\nDays: 7\n" in fake_llm.messages()[1]["content"]


def test_de_request_uses_de_candidates(client: TestClient, fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_plan(make_plan({"de-lidl-milk-1l": 1, "de-penny-tomatoes-500g": 2}))

    response = client.post("/generate", json={**BODY, "country": "DE"})

    assert response.status_code == 200
    assert response.json()["total"] == 4.07  # 1.09 + 2 x 1.49
    assert "\nat-" not in fake_llm.messages()[1]["content"]
