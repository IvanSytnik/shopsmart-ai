from fastapi.testclient import TestClient

from tests.conftest import ITEM, MEAL, FakeOpenAI, day, make_plan


def test_shopping_happy_path(client: TestClient, fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_plan(make_plan())

    response = client.post(
        "/generate", json={"supermarkets": ["Lidl", "Aldi"], "budget": 50, "family_size": 3}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == [ITEM]
    assert body["total_cost"] == 1.29
    assert body["notes"] == "Buy seasonal."
    assert body["menu"] is None
    assert body["generated_at"]

    assert fake_llm.calls == 1
    request = fake_llm.requests[0]
    assert request["model"] == "test-model"
    assert request["temperature"] == 0.1
    assert request["max_completion_tokens"] == 123
    assert request["response_format"]["type"] == "json_schema"
    assert request["response_format"]["json_schema"]["strict"] is True
    assert request["response_format"]["json_schema"]["name"] == "LLMPlan"

    system_prompt, user_message = (m["content"] for m in fake_llm.messages())
    assert "Create optimized weekly shopping list" in system_prompt
    assert "Supermarkets: Lidl, Aldi\nBudget: €50.0\nFamily: 3\n" in user_message
    assert user_message.endswith("Generate 15-25 items.")


def test_menu_happy_path(client: TestClient, fake_llm: FakeOpenAI) -> None:
    menu = [day("Montag"), day("Dienstag"), day("Mittwoch")]
    fake_llm.queue_plan(make_plan(menu=menu, notes="Gut."))

    response = client.post(
        "/generate",
        json={
            "supermarkets": ["Rewe"],
            "budget": 80,
            "language": "de",
            "mode": "menu",
            "days": 3,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert [d["day"] for d in body["menu"]] == ["Montag", "Dienstag", "Mittwoch"]
    assert body["menu"][0]["breakfast"] == MEAL
    assert body["items"] == [ITEM]
    assert fake_llm.calls == 1

    system_prompt, user_message = (m["content"] for m in fake_llm.messages())
    assert "Antworte auf Deutsch." in system_prompt
    assert "Create a 3-day meal plan" in system_prompt
    assert "Days: Montag, Dienstag, Mittwoch\n" in system_prompt
    assert user_message.endswith("Create 3-day meal plan with shopping list.")


def test_empty_notes_use_localized_fallback(client: TestClient, fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_plan(make_plan(notes=""))

    response = client.post(
        "/generate", json={"supermarkets": ["Lidl"], "budget": 50, "language": "uk"}
    )

    assert response.status_code == 200
    assert response.json()["notes"] == "Список оптимізовано під ваш бюджет."


def test_null_nutrition_is_returned_as_zero(client: TestClient, fake_llm: FakeOpenAI) -> None:
    soap = {**ITEM, "product": "Soap", "calories": None, "protein": None, "fat": None}
    fake_llm.queue_plan(make_plan(items=[{**soap, "carbs": None}]))

    response = client.post("/generate", json={"supermarkets": ["Lidl"], "budget": 50})

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert (item["calories"], item["protein"], item["fat"], item["carbs"]) == (0, 0, 0, 0)


def test_preferences_are_stripped(client: TestClient, fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_plan(make_plan())

    response = client.post(
        "/generate", json={"supermarkets": ["Lidl"], "budget": 50, "preferences": "  vegan  "}
    )

    assert response.status_code == 200
    assert "\nPreferences: vegan\n" in fake_llm.messages()[1]["content"]


def test_days_ignored_in_shopping_mode(client: TestClient, fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_plan(make_plan())

    response = client.post(
        "/generate", json={"supermarkets": ["Lidl"], "budget": 50, "mode": "shopping", "days": 2}
    )

    assert response.status_code == 200
    system_prompt, user_message = (m["content"] for m in fake_llm.messages())
    assert "meal plan" not in system_prompt
    assert "day" not in user_message
