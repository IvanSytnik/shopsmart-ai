"""POST /compare, GET /api/catalog/concepts and the ProductCatalog concept lookups.

A small AT catalog with easy numbers, prices as of 2026-11-02:

    concept         Billa                                   Hofer
    yogurt_natural  250 g €0.60; 1 kg €1.90                 500 g €1.00
    milk_whole      1 l €1.00; lactose-free 1 l €1.50       1 l €1.20
    eggs            10 pcs €3.00                            6 pcs €1.50
    bananas         1 kg €1.50                              -
    butter          250 g €2.00, promo €1.50 until 11-08    250 g €1.80
    dish_soap       500 ml €1.00 (non-food)                 -

A DE Hofer sells milk_whole for €0.10, which AT comparisons must ignore.
"""

import json
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.schemas.catalog import Catalog, LocalizedName
from app.schemas.compare import CompareRequest, CompareResponse, StoreComparison
from app.services.catalog import ProductCatalog
from app.services.comparison import compare
from tests.conftest import BODY, FakeOpenAI, make_plan

PRICE_DATE = "2026-11-02"
PROMO_RUNS = date(2026, 11, 5)  # the Billa butter promotion runs until 2026-11-08
PROMO_ENDED = date(2026, 11, 9)
VEG_GF = ("vegetarian", "gluten_free")


def product(
    product_id: str,
    concept_id: str,
    unit: str,
    pack_size: float,
    price: float,
    *,
    category: str = "dairy",
    diet_tags: tuple[str, ...] = VEG_GF,
    **extra: Any,
) -> dict[str, Any]:
    country, store = product_id.split("-")[:2]
    per_pack = None if category == "cleaning" else 100.0
    return {
        "id": product_id,
        "concept_id": concept_id,
        "country": country.upper(),
        "store": store.title(),
        "name": {"en": product_id, "uk": f"uk {product_id}", "de": f"de {product_id}"},
        "category": category,
        "unit": unit,
        "pack_size": pack_size,
        "price_eur": price,
        **dict.fromkeys(("kcal", "protein_g", "fat_g", "carbs_g"), per_pack),
        "diet_tags": list(diet_tags),
        "source_url": f"https://example.com/{product_id}",
        "price_date": PRICE_DATE,
        **extra,
    }


CATALOG_DATA = {
    "version": "test-compare",
    "price_date": PRICE_DATE,
    "products": [
        product("at-billa-yogurt-250g", "yogurt_natural", "kg", 0.25, 0.60),
        product("at-hofer-yogurt-500g", "yogurt_natural", "kg", 0.5, 1.00),
        product("at-billa-yogurt-1kg", "yogurt_natural", "kg", 1, 1.90),
        product("at-billa-milk-1l", "milk_whole", "l", 1, 1.00),
        product(
            "at-billa-milk-lactose-free-1l",
            "milk_whole",
            "l",
            1,
            1.50,
            diet_tags=(*VEG_GF, "lactose_free"),
        ),
        product("at-hofer-milk-1l", "milk_whole", "l", 1, 1.20),
        product("at-billa-eggs-10", "eggs", "pcs", 10, 3.00),
        product("at-hofer-eggs-6", "eggs", "pcs", 6, 1.50),
        product(
            "at-billa-bananas-1kg",
            "bananas",
            "kg",
            1,
            1.50,
            category="fruits",
            diet_tags=("vegetarian", "vegan", "gluten_free", "lactose_free"),
        ),
        product(
            "at-billa-butter-250g",
            "butter",
            "kg",
            0.25,
            1.50,
            regular_price_eur=2.00,
            promo_price_eur=1.50,
            promo_valid_until="2026-11-08",
        ),
        product("at-hofer-butter-250g", "butter", "kg", 0.25, 1.80),
        product(
            "at-billa-dish-soap-500ml",
            "dish_soap",
            "l",
            0.5,
            1.00,
            category="cleaning",
            diet_tags=(),
        ),
        product("de-hofer-milk-1l", "milk_whole", "l", 1, 0.10),
    ],
}

# Billa: 1.20 + 1.00 + 3.00 + 1.50 = 6.70, nothing missing.
# Hofer: 1.00 + 1.20 + 1.50 = 3.70, no bananas.
# Split: Billa milk 1.00 + bananas 1.50, Hofer yogurt 1.00 + eggs 1.50 = 5.00.
SHOPPING_LIST = {"yogurt_natural": 2, "milk_whole": 1, "eggs": 1, "bananas": 1}


def make_catalog(today: date = PROMO_RUNS) -> ProductCatalog:
    return ProductCatalog(Catalog.model_validate(CATALOG_DATA), today=lambda: today)


def compare_request(items: dict[str, int], **fields: Any) -> dict[str, Any]:
    return {
        "items": [{"concept_id": c, "quantity": q} for c, q in items.items()],
        "stores": ["Billa", "Hofer"],
        **fields,
    }


def run(items: dict[str, int], today: date = PROMO_RUNS, **fields: Any) -> CompareResponse:
    request = CompareRequest.model_validate(compare_request(items, **fields))
    return compare(make_catalog(today), request)


def ranking(response: CompareResponse, store: str) -> StoreComparison:
    return next(s for s in response.single_store_rankings if s.store == store)


def lines(comparison: StoreComparison) -> dict[str, tuple[str, int, Decimal]]:
    return {
        i.concept_id: (i.product_id, i.packs_needed, i.line_total_eur) for i in comparison.items
    }


# --- ProductCatalog --------------------------------------------------------------


def test_concepts_list_each_concept_once_per_country() -> None:
    catalog = make_catalog()
    concepts = {c.concept_id: c for c in catalog.concepts("AT")}

    assert list(concepts) == [
        "bananas",
        "butter",
        "dish_soap",
        "eggs",
        "milk_whole",
        "yogurt_natural",
    ]
    milk = concepts["milk_whole"]
    assert milk.names == [
        LocalizedName(en=i, uk=f"uk {i}", de=f"de {i}")
        for i in ("at-billa-milk-1l", "at-billa-milk-lactose-free-1l", "at-hofer-milk-1l")
    ]
    assert (milk.category, milk.unit, milk.stores, milk.reference_pack_size) == (
        "dairy",
        "l",
        ["Billa", "Hofer"],
        1.0,
    )
    assert concepts["yogurt_natural"].reference_pack_size == 0.25  # the smallest pack
    assert concepts["eggs"].reference_pack_size == 6
    assert concepts["bananas"].stores == ["Billa"]
    assert [(c.concept_id, c.stores) for c in catalog.concepts("DE")] == [("milk_whole", ["Hofer"])]


def test_products_for_concept_filter_by_country_store_and_diet() -> None:
    catalog = make_catalog()

    def ids(*args: Any, **kwargs: Any) -> list[str]:
        return [p.id for p in catalog.products_for_concept(*args, **kwargs)]

    assert ids("milk_whole", "AT") == [
        "at-billa-milk-1l",
        "at-billa-milk-lactose-free-1l",
        "at-hofer-milk-1l",
    ]
    assert ids("milk_whole", "AT", stores=["Hofer"]) == ["at-hofer-milk-1l"]
    assert ids("milk_whole", "AT", diets=["lactose_free"]) == ["at-billa-milk-lactose-free-1l"]
    assert ids("milk_whole", "DE") == ["de-hofer-milk-1l"]
    assert ids("dish_soap", "AT", diets=["vegan"]) == ["at-billa-dish-soap-500ml"]  # non-food
    assert ids("no_such_concept", "AT") == []


# --- comparison --------------------------------------------------------------------


def test_one_store_takes_its_cheapest_matching_product() -> None:
    response = run({"milk_whole": 2, "yogurt_natural": 1}, stores=["Billa"])

    [billa] = response.single_store_rankings
    assert lines(billa) == {
        "milk_whole": ("at-billa-milk-1l", 2, Decimal("2.00")),  # not the €1.50 lactose-free
        "yogurt_natural": ("at-billa-yogurt-250g", 1, Decimal("0.60")),
    }
    assert (billa.total_eur, billa.promo_savings_eur, billa.missing_concepts) == (
        Decimal("2.60"),
        Decimal("0"),
        [],
    )
    assert (response.recommended_strategy, response.recommended_store) == ("single_store", "Billa")
    assert [group.store for group in response.split_basket.stores] == ["Billa"]
    assert response.split_extra_savings_eur == 0
    assert (response.catalog_version, response.price_date) == ("test-compare", date(2026, 11, 2))


@pytest.mark.parametrize(
    ("concept", "quantity", "billa", "hofer"),
    [
        ("yogurt_natural", 1, (1, "0.60"), (1, "1.00")),  # 250 g; Hofer's pack holds 500 g
        ("yogurt_natural", 2, (2, "1.20"), (1, "1.00")),  # 500 g
        ("yogurt_natural", 3, (3, "1.80"), (2, "2.00")),  # 750 g
        ("eggs", 1, (1, "3.00"), (1, "1.50")),  # 6 eggs; Billa's pack holds 10
        ("eggs", 2, (2, "6.00"), (2, "3.00")),  # 12 eggs
        ("eggs", 5, (3, "9.00"), (5, "7.50")),  # 30 eggs
    ],
)
def test_quantity_counts_the_smallest_pack_and_every_store_buys_at_least_that(
    concept: str, quantity: int, billa: tuple[int, str], hofer: tuple[int, str]
) -> None:
    response = run({concept: quantity})

    for store, (packs, line_total) in (("Billa", billa), ("Hofer", hofer)):
        [item] = ranking(response, store).items
        assert (item.packs_needed, item.line_total_eur) == (packs, Decimal(line_total)), store


@pytest.mark.parametrize(
    ("quantity", "product_id", "packs", "line_total"),
    [
        (1, "at-billa-yogurt-250g", 1, "0.60"),  # the 1 kg pack is cheaper per kg, dearer here
        (3, "at-billa-yogurt-250g", 3, "1.80"),  # 750 g: 1.80 < 1.90
        (4, "at-billa-yogurt-1kg", 1, "1.90"),  # 1 kg: 1.90 < 2.40
    ],
)
def test_a_store_with_several_pack_sizes_sells_the_amount_for_the_least(
    quantity: int, product_id: str, packs: int, line_total: str
) -> None:
    response = run({"yogurt_natural": quantity}, stores=["Billa"])

    assert lines(ranking(response, "Billa")) == {
        "yogurt_natural": (product_id, packs, Decimal(line_total))
    }


def test_price_per_base_unit_is_per_kg_litre_or_piece() -> None:
    response = run({"yogurt_natural": 2, "milk_whole": 1, "eggs": 1})

    per_unit = {
        (item.store, item.concept_id, item.unit): item.price_per_base_unit_eur
        for comparison in response.single_store_rankings
        for item in comparison.items
    }
    assert per_unit == {
        ("Billa", "yogurt_natural", "kg"): Decimal("2.40"),
        ("Hofer", "yogurt_natural", "kg"): Decimal("2.00"),
        ("Billa", "milk_whole", "l"): Decimal("1.00"),
        ("Hofer", "milk_whole", "l"): Decimal("1.20"),
        ("Billa", "eggs", "pcs"): Decimal("0.30"),
        ("Hofer", "eggs", "pcs"): Decimal("0.25"),
    }


def test_a_running_promotion_is_the_price_and_shows_its_savings() -> None:
    response = run({"butter": 2}, today=PROMO_RUNS)

    billa = ranking(response, "Billa")
    [butter] = billa.items
    assert (
        butter.price_eur,
        butter.regular_price_eur,
        butter.promo_price_eur,
        butter.promo_valid_until,
    ) == (Decimal("1.50"), Decimal("2.00"), Decimal("1.50"), date(2026, 11, 8))
    assert (billa.total_eur, billa.promo_savings_eur) == (Decimal("3.00"), Decimal("1.00"))
    assert [s.store for s in response.single_store_rankings] == ["Billa", "Hofer"]  # 3.00 < 3.60


def test_an_ended_promotion_costs_the_regular_price() -> None:
    response = run({"butter": 2}, today=PROMO_ENDED)

    billa = ranking(response, "Billa")
    [butter] = billa.items
    assert (
        butter.price_eur,
        butter.regular_price_eur,
        butter.promo_price_eur,
        butter.promo_valid_until,
    ) == (Decimal("2.00"), Decimal("2.00"), None, None)
    assert (billa.total_eur, billa.promo_savings_eur) == (Decimal("4.00"), Decimal("0"))
    assert [s.store for s in response.single_store_rankings] == ["Hofer", "Billa"]  # 3.60 < 4.00


def test_diet_tags_filter_products_within_a_concept() -> None:
    response = run({"milk_whole": 1, "dish_soap": 1}, diet_tags=["lactose_free"])

    assert lines(ranking(response, "Billa")) == {
        "milk_whole": ("at-billa-milk-lactose-free-1l", 1, Decimal("1.50")),
        "dish_soap": ("at-billa-dish-soap-500ml", 1, Decimal("1.00")),  # non-food: any diet
    }
    hofer = ranking(response, "Hofer")
    assert (hofer.items, hofer.missing_concepts) == ([], ["milk_whole", "dish_soap"])


def test_fewer_missing_concepts_rank_first_even_when_dearer() -> None:
    response = run({"bananas": 1, "eggs": 1})

    assert [(s.store, s.total_eur, s.missing_concepts) for s in response.single_store_rankings] == [
        ("Billa", Decimal("4.50"), []),
        ("Hofer", Decimal("1.50"), ["bananas"]),
    ]


def test_an_unknown_concept_is_missing_everywhere() -> None:
    response = run({"caviar": 1})

    assert all(s.missing_concepts == ["caviar"] for s in response.single_store_rankings)
    assert (response.split_basket.stores, response.split_basket.missing_concepts) == (
        [],
        ["caviar"],
    )
    assert (response.recommended_strategy, response.recommended_store) == ("single_store", None)


def test_the_split_basket_takes_each_concept_where_it_costs_least() -> None:
    response = run(SHOPPING_LIST)

    split = response.split_basket
    assert [(g.store, [i.concept_id for i in g.items], g.total_eur) for g in split.stores] == [
        ("Billa", ["milk_whole", "bananas"], Decimal("2.50")),
        ("Hofer", ["yogurt_natural", "eggs"], Decimal("2.50")),
    ]
    assert (split.total_eur, split.missing_concepts) == (Decimal("5.00"), [])
    # Billa, the best single store (nothing missing), pays 6.70 for what the split buys for
    # 5.00; Hofer pays 3.70 for its three items, which cost 3.50 in the split.
    assert [s.store for s in response.single_store_rankings] == ["Billa", "Hofer"]
    assert response.split_extra_savings_eur == Decimal("1.70")
    assert split.total_savings_vs_worst_eur == Decimal("1.70")


def test_savings_against_the_best_and_the_worst_store() -> None:
    # Billa 1.00 + 3.00 = 4.00, Hofer 1.20 + 1.50 = 2.70, split 1.00 + 1.50 = 2.50.
    response = run({"milk_whole": 1, "eggs": 1})

    assert [s.store for s in response.single_store_rankings] == ["Hofer", "Billa"]
    assert response.split_extra_savings_eur == Decimal("0.20")  # vs Hofer, the best
    assert response.split_basket.total_savings_vs_worst_eur == Decimal("1.50")  # vs Billa


def test_a_store_missing_items_is_compared_on_the_items_it_has() -> None:
    # Billa has all three, each cheapest: 1.50 + 1.00 + 0.60 = 3.10, the whole split.
    # Hofer has no bananas and pays 1.20 + 1.00 = 2.20 for what costs 1.60 at Billa.
    response = run({"bananas": 1, "milk_whole": 1, "yogurt_natural": 1})

    assert [g.store for g in response.split_basket.stores] == ["Billa"]
    assert response.split_extra_savings_eur == 0
    assert response.split_basket.total_savings_vs_worst_eur == Decimal("0.60")


@pytest.mark.parametrize(
    ("threshold", "strategy", "store"),
    [
        (None, "single_store", "Billa"),  # default €3.00
        ("1.71", "single_store", "Billa"),
        ("1.70", "split_basket", None),  # saves exactly the threshold
        ("0", "split_basket", None),
    ],
)
def test_the_split_is_recommended_once_it_saves_min_split_savings(
    threshold: str | None, strategy: str, store: str | None
) -> None:
    fields = {} if threshold is None else {"min_split_savings_eur": threshold}

    response = run(SHOPPING_LIST, **fields)  # the split saves €1.70

    assert (response.recommended_strategy, response.recommended_store) == (strategy, store)


def test_a_split_within_one_store_is_never_recommended() -> None:
    response = run({"milk_whole": 1, "bananas": 1}, min_split_savings_eur="0")  # Billa wins both

    assert [group.store for group in response.split_basket.stores] == ["Billa"]
    assert (response.recommended_strategy, response.recommended_store) == ("single_store", "Billa")


# --- API -----------------------------------------------------------------------------


@pytest.fixture
def compare_client(tmp_path: Path, make_client: Callable[..., TestClient]) -> TestClient:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(CATALOG_DATA))
    return make_client(catalog_path=path)  # today's date: the butter promotion has ended


def test_concepts_endpoint(compare_client: TestClient) -> None:
    response = compare_client.get("/api/catalog/concepts")

    assert response.status_code == 200
    body = response.json()
    assert body["country"] == "AT"
    assert [c["concept_id"] for c in body["concepts"]][:2] == ["bananas", "butter"]
    assert body["concepts"][0] == {
        "concept_id": "bananas",
        "names": [
            {
                "en": "at-billa-bananas-1kg",
                "uk": "uk at-billa-bananas-1kg",
                "de": "de at-billa-bananas-1kg",
            }
        ],
        "category": "fruits",
        "unit": "kg",
        "stores": ["Billa"],
        "reference_pack_size": 1.0,
    }
    de = compare_client.get("/api/catalog/concepts", params={"country": "DE"}).json()
    assert [c["concept_id"] for c in de["concepts"]] == ["milk_whole"]


def test_concepts_endpoint_rejects_an_unknown_country(compare_client: TestClient) -> None:
    response = compare_client.get("/api/catalog/concepts", params={"country": "CH"})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_compare_endpoint(compare_client: TestClient) -> None:
    response = compare_client.post(
        "/compare", json=compare_request(SHOPPING_LIST, min_split_savings_eur=1.5)
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["recommended_strategy"], body["recommended_store"]) == ("split_basket", None)
    assert (body["split_extra_savings_eur"], body["split_basket"]["total_eur"]) == (1.7, 5.0)
    billa = body["single_store_rankings"][0]
    assert (billa["store"], billa["total_eur"], billa["missing_concepts"]) == ("Billa", 6.7, [])
    assert billa["items"][0] == {  # money is a number, like in /generate
        "concept_id": "yogurt_natural",
        "product_id": "at-billa-yogurt-250g",
        "names": {
            "en": "at-billa-yogurt-250g",
            "uk": "uk at-billa-yogurt-250g",
            "de": "de at-billa-yogurt-250g",
        },
        "store": "Billa",
        "packs_needed": 2,
        "pack_size": 0.25,
        "unit": "kg",
        "price_eur": 0.6,
        "regular_price_eur": 0.6,
        "promo_price_eur": None,
        "promo_valid_until": None,
        "line_total_eur": 1.2,
        "price_per_base_unit_eur": 2.4,
    }
    assert (body["catalog_version"], body["price_date"]) == ("test-compare", "2026-11-02")


def test_compare_uses_neither_the_llm_nor_the_generate_limits(
    make_client: Callable[..., TestClient], fake_llm: FakeOpenAI
) -> None:
    client = make_client(daily_generate_cap=1, rate_limit="1/minute")  # fixture catalog
    body = {"items": [{"concept_id": "milk_whole", "quantity": 1}], "stores": ["Lidl", "Penny"]}

    for _ in range(3):
        assert client.post("/compare", json=body).status_code == 200
    assert fake_llm.calls == 0

    fake_llm.queue_plan(make_plan())
    assert client.post("/generate", json=BODY).status_code == 200  # cap and limit still free


@pytest.mark.parametrize("stores", [["Billa", "Spar"], ["Lidl"]])
def test_compare_rejects_an_unknown_store(compare_client: TestClient, stores: list[str]) -> None:
    response = compare_client.post("/compare", json=compare_request({"eggs": 1}, stores=stores))

    assert response.status_code == 422
    assert response.json()["code"] == "unknown_store"


@pytest.mark.parametrize(
    "change",
    [
        {"items": []},
        {"items": [{"concept_id": "eggs", "quantity": 0}]},
        {"items": [{"concept_id": "eggs", "quantity": 51}]},
        {"items": [{"concept_id": "eggs", "quantity": 1}] * 2},
        {"items": [{"concept_id": f"c{i}", "quantity": 1} for i in range(51)]},
        {"items": [{"concept_id": "Eggs 10", "quantity": 1}]},
        {"stores": []},
        {"stores": ["Billa", "Billa"]},
        {"diet_tags": ["keto"]},
        {"min_split_savings_eur": -1},
        {"min_split_savings_eur": 1.234},
        {"country": "CH"},
    ],
)
def test_compare_rejects_invalid_input(compare_client: TestClient, change: dict[str, Any]) -> None:
    response = compare_client.post("/compare", json={**compare_request({"eggs": 1}), **change})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
