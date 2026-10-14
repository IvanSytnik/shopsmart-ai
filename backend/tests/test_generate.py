from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import FakeLLMClient

ITEM = {
    "product": "Milk",
    "quantity": "1L",
    "store": "Lidl",
    "approx_price": 1.29,
    "category": "dairy",
    "calories": 640,
    "protein": 34.0,
    "fat": 35.0,
    "carbs": 48.0,
}
MEAL = {"name": "Oatmeal", "description": "With apples", "calories": 350}


def day(name: str) -> dict[str, Any]:
    return {"day": name, "breakfast": MEAL, "lunch": MEAL, "dinner": MEAL, "snack": MEAL}


def test_shopping_happy_path(client: TestClient, fake_llm: FakeLLMClient) -> None:
    fake_llm.reply_with({"items": [ITEM], "total_cost": 1.29, "notes": "Buy seasonal."})

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

    call = fake_llm.completions.calls[-1]
    assert call["model"] == "test-model"
    assert call["temperature"] == 0.1
    assert call["max_tokens"] == 123
    system_prompt, user_message = fake_llm.last_messages
    assert "Create optimized weekly shopping list" in system_prompt
    assert "Supermarkets: Lidl, Aldi\nBudget: €50.0\nFamily: 3\n" in user_message
    assert user_message.endswith("Generate 15-25 items.")


def test_menu_happy_path(client: TestClient, fake_llm: FakeLLMClient) -> None:
    days = [day("Montag"), day("Dienstag"), day("Mittwoch")]
    fake_llm.reply_with({"menu": days, "items": [ITEM], "total_cost": 1.29, "notes": "Gut."})

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

    system_prompt, user_message = fake_llm.last_messages
    assert "Antworte auf Deutsch." in system_prompt
    assert "Create a 3-day meal plan" in system_prompt
    assert "Days: Montag, Dienstag, Mittwoch\n" in system_prompt
    assert user_message.endswith("Create 3-day meal plan with shopping list.")


def test_unfenced_json_and_missing_notes_use_localized_fallback(
    client: TestClient, fake_llm: FakeLLMClient
) -> None:
    fake_llm.reply_with({"items": [ITEM], "total_cost": 1.29}, fenced=False)

    response = client.post(
        "/generate", json={"supermarkets": ["Lidl"], "budget": 50, "language": "uk"}
    )

    assert response.status_code == 200
    assert response.json()["notes"] == "Список оптимізовано під ваш бюджет."


def test_preferences_are_stripped(client: TestClient, fake_llm: FakeLLMClient) -> None:
    fake_llm.reply_with({"items": [ITEM], "total_cost": 1.29})

    response = client.post(
        "/generate", json={"supermarkets": ["Lidl"], "budget": 50, "preferences": "  vegan  "}
    )

    assert response.status_code == 200
    assert "\nPreferences: vegan\n" in fake_llm.last_messages[1]


def test_days_ignored_in_shopping_mode(client: TestClient, fake_llm: FakeLLMClient) -> None:
    fake_llm.reply_with({"items": [ITEM], "total_cost": 1.29})

    response = client.post(
        "/generate", json={"supermarkets": ["Lidl"], "budget": 50, "mode": "shopping", "days": 2}
    )

    assert response.status_code == 200
    system_prompt, user_message = fake_llm.last_messages
    assert "meal plan" not in system_prompt
    assert "day" not in user_message
