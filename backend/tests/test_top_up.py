"""Shopping mode: deterministic kcal top-up after pricing and budget trimming."""

import random
from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services.catalog import ProductCatalog, load_catalog
from app.services.pricing import TOP_UP_EXCLUDED, PlanLine, PricedPlan, price_plan, top_up_kcal
from tests.conftest import APPLES, BODY, FIXTURE_CATALOG, MILK, RICE, FakeOpenAI, make_plan
from tests.test_catalog import PRODUCTION_CATALOG

OATS = "at-lidl-oat-flakes-500g"  # €0.89, 1860 kcal: best kcal per euro in AT Lidl/Penny
PASTA = "at-penny-pasta-500g"  # €0.99, 1780 kcal
CHIPS = "at-lidl-potato-chips-175g"  # snacks, never added
CHICKEN = "at-lidl-chicken-breast-500g"  # €5.99

FLOOR = 1600


@pytest.fixture(scope="module")
def catalog() -> ProductCatalog:
    return load_catalog(FIXTURE_CATALOG)


def plan_of(catalog: ProductCatalog, lines: dict[str, int]) -> PricedPlan:
    allowed = {p.id for p in catalog.catalog.products}
    return price_plan([PlanLine(i, n) for i, n in lines.items()], catalog, allowed)


def top_up(
    catalog: ProductCatalog,
    lines: dict[str, int],
    budget: float,
    target: float,
    diets: tuple[str, ...] = (),
    **limits: Any,
) -> tuple[PricedPlan, dict[str, int]]:
    candidates = catalog.candidates("AT", ["Lidl", "Penny"], diets)  # type: ignore[arg-type]
    return top_up_kcal(
        plan_of(catalog, lines),
        candidates,
        budget,
        target,
        max_packs_per_product=limits.get("max_packs", 3),
        max_kcal_share=limits.get("max_share", 0.35),
        skip_ids=limits.get("skip_ids", ()),
    )


# --- top_up_kcal ----------------------------------------------------------------


def test_adds_packs_until_the_target_is_reached(catalog: ProductCatalog) -> None:
    before = plan_of(catalog, {MILK: 2, APPLES: 2, RICE: 1})  # €8.85, 5820 kcal

    after, added = top_up(catalog, {MILK: 2, APPLES: 2, RICE: 1}, 50, 10_000)

    assert after.nutrition.kcal >= 10_000
    assert after.total <= Decimal(50)
    assert added  # recorded per product
    packs_before = {line.product.id: line.packs for line in before.lines}
    packs_after = {line.product.id: line.packs for line in after.lines}
    for product_id, n in added.items():
        assert packs_after[product_id] == packs_before.get(product_id, 0) + n


def test_prefers_products_already_in_the_list(catalog: ProductCatalog) -> None:
    # Rice (1528 kcal/€) is in the list; oats (2090 kcal/€) is only a candidate.
    # 11_700 kcal; another pack of pasta or rice would exceed 35% of the kcal, milk wouldn't.
    lines = {MILK: 4, APPLES: 4, PASTA: 2, RICE: 1}

    _, added = top_up(catalog, lines, 50, 12_000)

    assert added == {MILK: 1}


def test_then_uses_the_candidates_with_the_most_kcal_per_euro(catalog: ProductCatalog) -> None:
    lines = {MILK: 4, APPLES: 4, PASTA: 2, RICE: 1}

    _, added = top_up(catalog, lines, 50, 20_000, max_packs=1)

    # Milk and apples reach their pack cap; oats is the candidate with the most kcal per euro.
    assert list(added)[:3] == [MILK, APPLES, OATS]
    assert all(n == 1 for n in added.values())


def test_a_single_pack_above_the_kcal_share_is_not_added(catalog: ProductCatalog) -> None:
    after, added = top_up(catalog, {APPLES: 1}, 50, 5000)  # any pack is > 35% of 520 + it

    assert (after.total, added) == (Decimal("1.99"), {})


def test_does_nothing_at_or_above_the_target(catalog: ProductCatalog) -> None:
    plan = plan_of(catalog, {MILK: 2, APPLES: 2, RICE: 1})

    after, added = top_up(catalog, {MILK: 2, APPLES: 2, RICE: 1}, 50, 5820)

    assert (after, added) == (plan, {})


@pytest.mark.parametrize("seed", range(30))
def test_never_exceeds_the_budget(catalog: ProductCatalog, seed: int) -> None:
    rng = random.Random(seed)
    lines = {MILK: rng.randint(1, 3), APPLES: rng.randint(1, 3), CHICKEN: 1}
    budget = float(plan_of(catalog, lines).total) + rng.randint(0, 2000) / 100

    after, _ = top_up(catalog, lines, budget, 1_000_000)

    assert after.total <= Decimal(str(budget))


def test_skips_packs_that_do_not_fit_the_remaining_budget(catalog: ProductCatalog) -> None:
    # €8.85 spent, €0.80 left: only oats-like products under €0.80 could fit; none exist.
    after, added = top_up(catalog, {MILK: 2, APPLES: 2, RICE: 1}, 9.65, 1_000_000)

    assert added == {}
    assert after.total == Decimal("8.85")


def test_caps_packs_per_product_and_kcal_share(catalog: ProductCatalog) -> None:
    after, added = top_up(catalog, {MILK: 2, APPLES: 2, RICE: 1}, 1000, 1_000_000)

    assert added and max(added.values()) == 3
    kcal = after.nutrition.kcal
    for line in after.lines:
        if line.product.id in added and line.nutrition is not None:
            assert line.nutrition.kcal <= 0.35 * kcal


def test_never_adds_excluded_categories_or_skipped_ids(catalog: ProductCatalog) -> None:
    lines = {CHIPS: 4, MILK: 4, APPLES: 4}

    after, added = top_up(catalog, lines, 1000, 1_000_000, skip_ids={OATS, RICE})

    assert added
    products = {line.product.id: line.product for line in after.lines}
    assert CHIPS not in added and OATS not in added and RICE not in added
    assert not {products[i].category for i in added} & TOP_UP_EXCLUDED


def test_respects_the_diet_filtered_candidates(catalog: ProductCatalog) -> None:
    lines = {APPLES: 4, PASTA: 2, RICE: 1}

    _, added = top_up(catalog, lines, 1000, 1_000_000, diets=("vegan",))

    assert set(added) - set(lines)  # candidates were used too
    for product_id in added:
        product = catalog.get(product_id)
        assert product is not None and "vegan" in product.diet_tags


# --- through /generate ------------------------------------------------------------


@pytest.fixture
def floor_client(make_client: Callable[..., TestClient]) -> TestClient:
    return make_client(min_kcal_per_person_day=FLOOR)


def test_shopping_list_is_topped_up_to_the_floor(
    floor_client: TestClient, fake_llm: FakeOpenAI
) -> None:
    fake_llm.queue_plan(make_plan())  # €8.85, 5820 kcal = 416 per person and day

    body = floor_client.post("/generate", json={**BODY, "family_size": 1}).json()

    assert body["kcal_per_person_day"] >= FLOOR
    assert body["total"] <= body["budget"]
    assert body["warnings"] == ["kcal_topped_up"]
    assert fake_llm.calls == 1  # deterministic, no repair call


def test_low_kcal_when_the_floor_is_unreachable(
    floor_client: TestClient, fake_llm: FakeOpenAI
) -> None:
    fake_llm.queue_plan(make_plan())

    body = floor_client.post("/generate", json={**BODY, "family_size": 10}).json()

    assert body["kcal_per_person_day"] < FLOOR
    assert body["total"] <= body["budget"]
    assert body["warnings"] == ["low_kcal", "kcal_topped_up"]


def test_top_up_keeps_store_and_diet_filters(
    floor_client: TestClient, fake_llm: FakeOpenAI
) -> None:
    fake_llm.queue_plan(make_plan({APPLES: 2, RICE: 1}))

    body = floor_client.post("/generate", json={**BODY, "diets": ["vegan"]}).json()

    catalog = load_catalog(FIXTURE_CATALOG)
    assert "kcal_topped_up" in body["warnings"]
    for item in body["items"]:
        product = catalog.get(item["product_id"])
        assert product is not None
        assert (product.country, product.store in BODY["supermarkets"]) == ("AT", True)
        assert "vegan" in product.diet_tags


def test_trimmed_products_are_not_added_back(
    floor_client: TestClient, fake_llm: FakeOpenAI
) -> None:
    fake_llm.queue_plan(make_plan({CHICKEN: 2, RICE: 1}))  # €14.27, trimmed to €13.50

    body = floor_client.post("/generate", json={**BODY, "budget": 13.5}).json()

    trimmed = [(t["product_id"], t["from_packs"], t["to_packs"]) for t in body["trimmed"]]
    assert trimmed == [(CHICKEN, 2, 1)]
    chicken = [i for i in body["items"] if i["product_id"] == CHICKEN]
    assert chicken[0]["packs"] == 1
    assert body["total"] <= 13.5
    assert body["warnings"] == ["low_kcal", "budget_trimmed", "kcal_topped_up"]


def test_menu_mode_is_not_topped_up(
    make_client: Callable[..., TestClient], fake_llm: FakeOpenAI
) -> None:
    menu = {**BODY, "mode": "menu", "days": 1}
    fake_llm.queue_plan(make_plan(days=1), times=2)
    with_top_up = make_client(min_kcal_per_person_day=1000).post("/generate", json=menu).json()
    without = make_client(min_kcal_per_person_day=1000, top_up_max_packs_per_product=0).post(
        "/generate", json=menu
    )

    assert "kcal_topped_up" not in with_top_up["warnings"]
    for key in ("items", "total", "kcal_per_person_day", "warnings", "menu"):
        assert with_top_up[key] == without.json()[key]


def test_billa_50_euro_two_people(
    make_client: Callable[..., TestClient], fake_llm: FakeOpenAI
) -> None:
    """The live report: Billa, €50, 2 people, shopping -> ~€24 and ~1100 kcal, no warning."""
    client = make_client(catalog_path=PRODUCTION_CATALOG, min_kcal_per_person_day=FLOOR)
    lines = {
        "at-billa-eggs-m-10": 1,
        "at-billa-uht-whole-milk-1l": 2,
        "at-billa-bananas-1kg": 1,
        "at-billa-potatoes-2kg": 1,
        "at-billa-organic-spaghetti-500g": 2,
        "at-billa-wheat-toast-500g": 1,
        "at-billa-onions-1kg": 1,
        "at-billa-natural-yogurt-250g": 2,
        "at-billa-cherry-tomatoes-500g": 1,
        "at-billa-apple-juice-1l": 1,
        "at-billa-gouda-slices-400g": 1,
        "at-billa-butter-250g": 1,
        "at-billa-oats-500g": 1,
    }
    fake_llm.queue_plan(make_plan(lines))
    request = {"country": "AT", "supermarkets": ["Billa"], "budget": 50, "family_size": 2}

    body = client.post("/generate", json=request).json()

    kcal_before = 15606 / 14  # what the LLM's list alone buys per person and day
    assert kcal_before < FLOOR
    assert body["total"] <= 50
    assert body["kcal_per_person_day"] >= FLOOR or "low_kcal" in body["warnings"]
    assert body["kcal_per_person_day"] >= FLOOR  # the catalog's staples make it reachable
    assert "kcal_topped_up" in body["warnings"]
    assert all(i["store"] == "Billa" for i in body["items"])
