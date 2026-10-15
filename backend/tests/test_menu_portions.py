"""Menu mode end to end: the LLM gives per-person portions, the server buys the packs."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import APPLES, BODY, MILK, RICE, FakeOpenAI, ing, make_plan, meal

CHICKEN = "at-lidl-chicken-breast-500g"  # 0.5 kg, €5.99
CHIPS = "at-lidl-potato-chips-175g"  # 0.175 kg, €1.79
EGGS = "de-lidl-eggs-10"  # 10 pcs
PIZZA = "at-penny-frozen-pizza-350g"  # 0.35 kg, portion unit "pack", 840 kcal
MENU_1_DAY = {**BODY, "mode": "menu", "days": 1}


def one_day(*meals: dict[str, Any], snack: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    breakfast, lunch, dinner = meals
    return [
        {"day": "Monday", "breakfast": breakfast, "lunch": lunch, "dinner": dinner, "snack": snack}
    ]


def test_menu_schema_has_portions_and_no_lines(client: TestClient, fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_plan(make_plan(days=1))
    fake_llm.queue_plan(make_plan())

    client.post("/generate", json=MENU_1_DAY)
    client.post("/generate", json=BODY)

    menu, shopping = (r["response_format"]["json_schema"] for r in fake_llm.requests)
    assert menu["name"] == "LLMMenuPlan"
    assert list(menu["schema"]["properties"]) == ["menu", "notes"]
    assert "LLMLine" not in menu["schema"]["$defs"]
    amount = menu["schema"]["$defs"]["LLMIngredient"]["properties"]["amount_per_person"]
    assert (amount["type"], amount["minimum"], amount["maximum"]) == ("number", 0.25, 800)
    assert shopping["name"] == "LLMShoppingPlan"
    assert list(shopping["schema"]["properties"]) == ["lines", "notes"]


@pytest.mark.parametrize(
    ("dinner_g", "packs", "total"),
    [(80, 1, 5.99), (100, 2, 11.98)],
    ids=["480g-one-pack", "520g-two-packs"],
)
def test_packs_are_derived_from_portions(
    client: TestClient, fake_llm: FakeOpenAI, dinner_g: int, packs: int, total: float
) -> None:
    # (80 + 80 + dinner_g) g x 2 people of chicken, sold in 500 g packs.
    menu = one_day(meal(ing(CHICKEN, 80)), meal(ing(CHICKEN, 80)), meal(ing(CHICKEN, dinner_g)))
    fake_llm.queue_plan(make_plan(days=1, menu=menu))

    response = client.post("/generate", json=MENU_1_DAY)

    assert response.status_code == 200
    body = response.json()
    assert [(i["product_id"], i["packs"]) for i in body["items"]] == [(CHICKEN, packs)]
    assert body["total"] == total
    # Eaten, not bought: (160 + dinner_g) g x 1.1 kcal/g per person.
    assert body["kcal_per_person_day"] == round((160 + dinner_g) * 1.1)
    assert body["kcal_basis"] == "menu"


def test_pieces_are_counted_per_person(client: TestClient, fake_llm: FakeOpenAI) -> None:
    menu = one_day(
        meal(ing(EGGS, 2), name="Eggs"),
        meal(ing("de-penny-pasta-500g", 100), name="Pasta"),
        meal(ing(EGGS, 1), ing("de-penny-pasta-500g", 100), name="Pasta with egg"),
    )
    fake_llm.queue_plan(make_plan(days=1, menu=menu))

    response = client.post("/generate", json={**MENU_1_DAY, "country": "DE", "family_size": 4})

    assert response.status_code == 200
    packs = {i["product_id"]: i["packs"] for i in response.json()["items"]}
    assert packs[EGGS] == 2  # 3 eggs x 4 people = 12 -> 2 boxes of 10
    assert packs["de-penny-pasta-500g"] == 2  # 200 g x 4 = 800 g -> 2 x 500 g
    system_prompt, user_message = (m["content"] for m in fake_llm.messages())
    assert "| portion: pcs | 78 kcal/pc\n" in user_message
    assert "eggs 1-3 pcs" in system_prompt


def test_too_many_pieces_are_clamped_and_used_for_the_packs(
    client: TestClient, fake_llm: FakeOpenAI, caplog: pytest.LogCaptureFixture
) -> None:
    pasta = meal(ing("de-penny-pasta-500g", 100))
    fake_llm.queue_plan(make_plan(days=1, menu=one_day(meal(ing(EGGS, 9)), pasta, pasta)))

    response = client.post("/generate", json={**MENU_1_DAY, "country": "DE", "family_size": 4})

    assert response.status_code == 200
    assert fake_llm.calls == 1
    body = response.json()
    # 9 eggs is above the 6 pcs limit: 6 x 4 people = 24 -> 3 boxes (9 would need 4).
    assert {i["product_id"]: i["packs"] for i in body["items"]}[EGGS] == 3
    assert body["menu"][0]["breakfast"]["ingredients"] == [
        {"product_id": EGGS, "amount_per_person": 6}
    ]
    assert f"Clamped portion of {EGGS} from 9 to 6 pcs" in caplog.text


def test_tiny_portions_are_raised_to_the_minimum(
    client: TestClient, fake_llm: FakeOpenAI, caplog: pytest.LogCaptureFixture
) -> None:
    menu = one_day(meal(ing(APPLES, 3), ing(MILK, 4)), meal(ing(RICE, 100)), meal(ing(RICE, 100)))
    fake_llm.queue_plan(make_plan(days=1, menu=menu))

    response = client.post("/generate", json=MENU_1_DAY)

    assert response.status_code == 200
    assert fake_llm.calls == 1
    assert response.json()["menu"][0]["breakfast"]["ingredients"] == [
        {"product_id": APPLES, "amount_per_person": 5},
        {"product_id": MILK, "amount_per_person": 5},
    ]
    assert f"Clamped portion of {APPLES} from 3 to 5 g" in caplog.text
    assert f"Clamped portion of {MILK} from 4 to 5 ml" in caplog.text


@pytest.mark.parametrize(
    ("product_id", "raw", "grams"),
    [(CHICKEN, 1, 500), (RICE, 0.5, 500), (CHIPS, 2, 350), (CHICKEN, 0.25, 125)],
)
def test_tiny_g_ml_portions_are_read_as_packs(
    client: TestClient,
    fake_llm: FakeOpenAI,
    caplog: pytest.LogCaptureFixture,
    product_id: str,
    raw: float,
    grams: int,
) -> None:
    menu = one_day(meal(ing(product_id, raw)), meal(ing(RICE, 100)), meal(ing(MILK, 200)))
    fake_llm.queue_plan(make_plan(days=1, menu=menu))

    response = client.post("/generate", json=MENU_1_DAY)

    assert response.status_code == 200
    assert fake_llm.calls == 1
    breakfast = response.json()["menu"][0]["breakfast"]["ingredients"]
    assert breakfast == [{"product_id": product_id, "amount_per_person": grams}]
    assert f"Read portion of {product_id} as {raw:g} packs: {grams} g" in caplog.text


def test_milk_read_as_one_pack_is_then_clamped(
    client: TestClient, fake_llm: FakeOpenAI, caplog: pytest.LogCaptureFixture
) -> None:
    menu = one_day(meal(ing(MILK, 1)), meal(ing(RICE, 100)), meal(ing(RICE, 100)))
    fake_llm.queue_plan(make_plan(days=1, menu=menu))

    response = client.post("/generate", json=MENU_1_DAY)

    # 1 pack = 1000 ml, above the 800 ml limit.
    assert response.json()["menu"][0]["breakfast"]["ingredients"][0]["amount_per_person"] == 800
    assert f"Clamped portion of {MILK} from 1000 to 800 ml" in caplog.text


def test_meals_without_ingredients_are_repaired(client: TestClient, fake_llm: FakeOpenAI) -> None:
    bad = make_plan(days=1)
    bad["menu"][0]["lunch"]["ingredients"] = []
    fake_llm.queue_plan(bad)
    fake_llm.queue_plan(make_plan(days=1))

    client.post("/generate", json=MENU_1_DAY)

    assert fake_llm.messages(1)[-1]["content"] == (
        "These meals have no ingredients: Day 1 lunch. Every meal needs at least one ingredient."
    )


def test_pack_portions_buy_whole_packs(client: TestClient, fake_llm: FakeOpenAI) -> None:
    menu = one_day(
        meal(ing(RICE, 100)),
        meal(ing(RICE, 100)),
        meal(ing(PIZZA, 0.5), name="Half a pizza"),
    )
    fake_llm.queue_plan(make_plan(days=1, menu=menu))

    response = client.post("/generate", json={**MENU_1_DAY, "family_size": 3})

    assert response.status_code == 200
    body = response.json()
    pizza = next(i for i in body["items"] if i["product_id"] == PIZZA)
    assert (pizza["packs"], pizza["unit"], pizza["portion_unit"]) == (2, "kg", "pack")  # 1.5
    assert body["menu"][0]["dinner"]["ingredients"] == [
        {"product_id": PIZZA, "amount_per_person": 0.5}
    ]
    # Per person: 200 g rice (700 kcal) + half a pizza (420 kcal).
    assert body["kcal_per_person_day"] == 1120
    user_message = fake_llm.messages()[1]["content"]
    assert (
        f"\n{PIZZA} | Frozen pizza margherita | 0.35 kg | €2.79 | Penny | frozen | "
        "portion: pack (1 = one whole 350 g pack) | 840 kcal/pack\n" in user_message
    )
    assert (
        "packs (pack: a fraction of one whole pack in steps of 0.25"
        in (fake_llm.messages()[0]["content"])
    )


def test_portions_above_max_kcal_are_scaled_down(
    make_client: Callable[..., TestClient], fake_llm: FakeOpenAI
) -> None:
    client = make_client(max_kcal_per_person_day=2000)
    huge = one_day(meal(ing(RICE, 800)), meal(ing(RICE, 800)), meal(ing(RICE, 800)))
    fake_llm.queue_plan(make_plan(days=1, menu=huge))  # 2400 g x 3.5 kcal/g = 8400

    response = client.post("/generate", json=MENU_1_DAY)

    assert response.status_code == 200
    assert fake_llm.calls == 1
    body = response.json()
    # Factor 2000 / 8400 x 0.95 = 0.226: 800 g -> 181 -> 180 g. 540 g = 1890 kcal.
    assert body["menu"][0]["lunch"]["ingredients"] == [
        {"product_id": RICE, "amount_per_person": 180}
    ]
    assert body["kcal_per_person_day"] == 1890
    assert [(i["product_id"], i["packs"]) for i in body["items"]] == [(RICE, 2)]  # 1080 g


def test_scaled_portions_are_rounded_then_clamped(
    make_client: Callable[..., TestClient], fake_llm: FakeOpenAI, caplog: pytest.LogCaptureFixture
) -> None:
    client = make_client(min_kcal_per_person_day=1600)
    pasta = meal(ing("de-penny-pasta-500g", 100))
    # 5 eggs (390 kcal) + 2 x 100 g pasta (712) = 1102 kcal: factor 1.52.
    day_menu = one_day(meal(ing(EGGS, 5)), pasta, pasta)
    fake_llm.queue_plan(make_plan(days=1, menu=day_menu), times=2)

    response = client.post("/generate", json={**MENU_1_DAY, "country": "DE"})

    assert response.status_code == 200
    body = response.json()
    # Eggs 5 x 1.52 = 7.6 -> 8, above 6 pcs -> 6. Pasta 152.4 g -> 150 g.
    assert body["menu"][0]["breakfast"]["ingredients"] == [
        {"product_id": EGGS, "amount_per_person": 6}
    ]
    assert body["menu"][0]["lunch"]["ingredients"][0]["amount_per_person"] == 150
    assert f"Clamped portion of {EGGS} from 8 to 6 pcs" in caplog.text
    # 6 x 78 + 300 g x 3.56 = 1536: still below 1600, so a repair was asked for.
    assert fake_llm.calls == 2
    assert (body["kcal_per_person_day"], body["warnings"]) == (1536, ["low_kcal"])


def test_over_budget_menu_repair_names_the_three_most_expensive_ingredients(
    client: TestClient, fake_llm: FakeOpenAI
) -> None:
    # 2 people: chicken 1200 g -> 3 packs (17.97), chips 200 g -> 2 (3.58), rice 500 g -> 1
    # (2.29), apples 400 g -> 1 (1.99), milk 500 ml -> 1 (1.29): 27.12.
    menu = one_day(
        meal(ing(MILK, 250), ing(APPLES, 200)),
        meal(ing(CHICKEN, 300), ing(RICE, 125)),
        meal(ing(CHICKEN, 300), ing(RICE, 125)),
        snack=meal(ing(CHIPS, 100)),
    )
    fake_llm.queue_plan(make_plan(days=1, menu=menu))
    fake_llm.queue_plan(make_plan(days=1))

    response = client.post("/generate", json={**MENU_1_DAY, "budget": 15})

    assert response.status_code == 200
    assert fake_llm.messages(1)[-1]["content"] == (
        "Your previous menu costs €27.12 at catalog prices, €12.12 over the budget of €15.00. "
        f"The most expensive ingredients are: Chicken breast ({CHICKEN}) €17.97, Potato chips "
        f"({CHIPS}) €3.58, Long-grain rice ({RICE}) €2.29. Return the full menu again with "
        "smaller portions, fewer of these or cheaper products so the total is at most €15.00."
    )


def test_shopping_mode_keeps_the_llm_pack_counts(client: TestClient, fake_llm: FakeOpenAI) -> None:
    fake_llm.queue_plan(make_plan({CHICKEN: 3, MILK: 1}))

    response = client.post("/generate", json=BODY)

    assert response.status_code == 200
    body = response.json()
    assert [(i["product_id"], i["packs"]) for i in body["items"]] == [(CHICKEN, 3), (MILK, 1)]
    assert (body["kcal_basis"], body["kcal_per_person_day"]) == ("purchased", 164)  # 2290/14
    assert "amount_per_person" not in fake_llm.messages()[0]["content"]
