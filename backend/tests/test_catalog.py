import json
import logging
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.catalog import NON_FOOD_CATEGORIES, Catalog
from app.services.catalog import CatalogLoadError, ProductCatalog, load_catalog
from tests.conftest import BODY, FIXTURE_CATALOG, MILK, FakeOpenAI, make_plan, make_settings

FIXTURE = Path(__file__).parent / "fixtures" / "catalog_small.json"
PRODUCTION_CATALOG = Path(__file__).parents[1] / "app" / "data" / "catalog.json"


@pytest.fixture(scope="module")
def catalog() -> ProductCatalog:
    return load_catalog(FIXTURE)


def fixture_data() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text())


@pytest.fixture
def write_catalog(tmp_path: Path) -> Callable[[dict[str, Any]], Path]:
    def write(data: dict[str, Any]) -> Path:
        path = tmp_path / "catalog.json"
        path.write_text(json.dumps(data))
        return path

    return write


# --- loading -----------------------------------------------------------------


def test_production_catalog_is_valid() -> None:
    catalog = load_catalog(PRODUCTION_CATALOG)

    assert len(catalog) > 0
    assert catalog.catalog.version.startswith("at-")


def test_app_starts_with_the_production_catalog() -> None:
    app = create_app(make_settings(catalog_path=PRODUCTION_CATALOG))
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    countries = client.get("/api/catalog/meta").json()["countries"]
    assert countries["AT"] == ["Billa", "Hofer"]
    assert countries["DE"] == []


def test_fixture_catalog_loads(catalog: ProductCatalog) -> None:
    assert len(catalog) == 39
    assert {p.country for p in catalog.catalog.products} == {"AT", "DE"}
    assert {p.store for p in catalog.catalog.products} == {"Lidl", "Penny"}


def _break_first_product(**changes: Any) -> dict[str, Any]:
    data = fixture_data()
    data["products"][0].update(changes)
    return data


@pytest.mark.parametrize(
    ("case", "data", "message"),
    [
        (
            "duplicate id",
            {**fixture_data(), "products": fixture_data()["products"][:2] * 2},
            "duplicate product ids: at-lidl-milk-1l, at-lidl-oat-drink-1l",
        ),
        (
            "vegan without vegetarian",
            _break_first_product(diet_tags=["vegan"]),
            "vegan product must also be tagged vegetarian",
        ),
        ("partial nutrition", _break_first_product(fat_g=None), "all set or all null"),
        ("price with 3 decimals", _break_first_product(price_eur=1.299), "decimal places"),
        ("zero price", _break_first_product(price_eur=0), "price_eur"),
        ("zero pack size", _break_first_product(pack_size=0), "pack_size"),
        (
            "fractional pack",
            _break_first_product(unit="pack", pack_size=0.4),
            "whole number for unit 'pack'",
        ),
        (
            "portion unit that doesn't fit the unit",
            _break_first_product(portion_unit="g"),  # milk is sold by the litre
            "portion_unit 'g' doesn't fit unit 'l'",
        ),
        ("unknown portion unit", _break_first_product(portion_unit="cup"), "portion_unit"),
        (
            "fractional pcs",
            _break_first_product(unit="pcs", pack_size=2.5),
            "whole number for unit 'pcs'",
        ),
        ("negative kcal", _break_first_product(kcal=-1), "kcal"),
        ("bad slug", _break_first_product(id="Milk 1L"), "id"),
        ("unknown country", _break_first_product(country="CH"), "country"),
        ("unknown category", _break_first_product(category="toys"), "category"),
        ("unknown unit", _break_first_product(unit="g"), "unit"),
        ("unknown diet tag", _break_first_product(diet_tags=["keto"]), "diet_tags"),
        ("duplicate diet tag", _break_first_product(diet_tags=["vegetarian"] * 2), "duplicates"),
        ("missing name", _break_first_product(name={"en": "Milk", "de": "Milch"}), "uk"),
        ("bad url", _break_first_product(source_url="not a url"), "source_url"),
        ("extra field", _break_first_product(discount=0.5), "discount"),
    ],
)
def test_invalid_catalog_fails_fast(
    write_catalog: Callable[[dict[str, Any]], Path],
    case: str,
    data: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(CatalogLoadError, match="invalid catalog") as info:
        load_catalog(write_catalog(data))

    assert message in str(info.value), case


@pytest.mark.parametrize(
    ("unit", "pack_size"), [("pack", 1), ("pcs", 10), ("kg", 0.4), ("l", 0.33)]
)
def test_valid_pack_sizes(
    write_catalog: Callable[[dict[str, Any]], Path], unit: str, pack_size: float
) -> None:
    catalog = load_catalog(write_catalog(_break_first_product(unit=unit, pack_size=pack_size)))

    assert catalog.get("at-lidl-milk-1l") is not None


def test_portion_unit_defaults_from_the_unit() -> None:
    catalog = load_catalog(FIXTURE_CATALOG)

    units = {
        product_id: (p.unit, p.portion_unit)
        for product_id in ("at-lidl-milk-1l", "at-lidl-apples-1kg", "de-lidl-eggs-10")
        if (p := catalog.get(product_id)) is not None
    }
    assert units == {
        "at-lidl-milk-1l": ("l", "ml"),
        "at-lidl-apples-1kg": ("kg", "g"),
        "de-lidl-eggs-10": ("pcs", "pcs"),
    }
    pizza = catalog.get("at-penny-frozen-pizza-350g")
    assert pizza is not None and (pizza.unit, pizza.portion_unit) == ("kg", "pack")


def test_missing_catalog_file_fails_fast(tmp_path: Path) -> None:
    with pytest.raises(CatalogLoadError, match="cannot read catalog"):
        load_catalog(tmp_path / "nope.json")


def test_malformed_json_fails_fast(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    path.write_text("{not json")

    with pytest.raises(CatalogLoadError, match="invalid catalog"):
        load_catalog(path)


def test_app_refuses_to_start_with_invalid_catalog(
    write_catalog: Callable[[dict[str, Any]], Path],
) -> None:
    path = write_catalog(_break_first_product(diet_tags=["vegan"]))

    with pytest.raises(CatalogLoadError):
        create_app(make_settings(catalog_path=path))


# --- queries -----------------------------------------------------------------


def test_get(catalog: ProductCatalog) -> None:
    product = catalog.get("de-lidl-salmon-250g")

    assert product is not None
    assert (product.store, product.country, product.category) == ("Lidl", "DE", "fish")
    assert catalog.get("no-such-product") is None


def test_candidates_filter_by_country(catalog: ProductCatalog) -> None:
    candidates = catalog.candidates("DE", ["Lidl", "Penny"], [])

    assert len(candidates) == 19
    assert {p.country for p in candidates} == {"DE"}


def test_candidates_filter_by_store(catalog: ProductCatalog) -> None:
    candidates = catalog.candidates("AT", ["Penny"], [])

    assert {p.store for p in candidates} == {"Penny"}
    assert len(candidates) == 9


def test_candidates_same_store_name_in_other_country_is_excluded(
    catalog: ProductCatalog,
) -> None:
    ids = {p.id for p in catalog.candidates("AT", ["Lidl"], [])}

    assert "at-lidl-milk-1l" in ids
    assert "de-lidl-milk-1l" not in ids


def test_candidates_unknown_store_is_empty(catalog: ProductCatalog) -> None:
    assert catalog.candidates("AT", ["Billa"], []) == []


def test_vegan_excludes_dairy_meat_and_fish(catalog: ProductCatalog) -> None:
    for country in ("AT", "DE"):
        candidates = catalog.candidates(country, ["Lidl", "Penny"], ["vegan"])
        food = [p for p in candidates if p.category not in NON_FOOD_CATEGORIES]

        assert food
        assert all("vegan" in p.diet_tags for p in food)
        assert not {p.category for p in candidates} & {"dairy", "meat", "fish"}
    ids = {p.id for p in catalog.candidates("AT", ["Lidl", "Penny"], ["vegan"])}
    assert "at-penny-frozen-pizza-350g" not in ids  # vegetarian, not vegan


def test_vegetarian_keeps_dairy_drops_meat(catalog: ProductCatalog) -> None:
    categories = {p.category for p in catalog.candidates("DE", ["Lidl", "Penny"], ["vegetarian"])}

    assert "dairy" in categories
    assert not categories & {"meat", "fish"}


def test_multiple_diets_require_every_tag(catalog: ProductCatalog) -> None:
    candidates = catalog.candidates("AT", ["Lidl", "Penny"], ["vegan", "gluten_free"])
    ids = {p.id for p in candidates}

    assert "at-lidl-apples-1kg" in ids
    assert "at-penny-pasta-500g" not in ids  # vegan but not gluten-free
    assert "at-lidl-oat-drink-1l" not in ids


def test_non_food_is_kept_under_any_diet(catalog: ProductCatalog) -> None:
    ids = {p.id for p in catalog.candidates("AT", ["Lidl", "Penny"], ["vegan", "gluten_free"])}

    assert {"at-lidl-dish-soap-500ml", "at-penny-toothpaste-75ml"} <= ids


# --- concepts and promotions -------------------------------------------------

AT_MILK = "at-lidl-milk-1l"  # the first fixture product: €1.29, price_date 2026-10-01


def _milk_promo(until: str, **changes: Any) -> dict[str, Any]:
    """The fixture with milk at €1.49, on promotion for €1.29 (its price) until `until`."""
    promo = {"regular_price_eur": 1.49, "promo_price_eur": 1.29, "promo_valid_until": until}
    return _break_first_product(**{**promo, **changes})


def _without_concept_id() -> dict[str, Any]:
    data = fixture_data()
    del data["products"][0]["concept_id"]
    return data


def _without_concept_name(concept_id: str) -> dict[str, Any]:
    data = fixture_data()
    data["concepts"] = [c for c in data["concepts"] if c["concept_id"] != concept_id]
    return data


@pytest.mark.parametrize(
    ("case", "data", "message"),
    [
        ("missing concept_id", _without_concept_id(), "concept_id"),
        (
            "concept without a name",
            _without_concept_name("milk_whole"),
            "concepts without a name: milk_whole",
        ),
        (
            "concept named twice",
            {**fixture_data(), "concepts": fixture_data()["concepts"][:2] * 2},
            "concepts named twice: apples, bananas",
        ),
        (
            "concept name in two languages",
            {
                **fixture_data(),
                "concepts": [{"concept_id": "milk_whole", "name": {"en": "Milk", "de": "Milch"}}],
            },
            "uk",
        ),
        ("kebab-case concept_id", _break_first_product(concept_id="milk-whole-1l"), "concept_id"),
        (
            "promo price without end date",
            _break_first_product(regular_price_eur=1.49, promo_price_eur=1.29),
            "promo_price_eur and promo_valid_until must be set together",
        ),
        (
            "end date without promo price",
            _break_first_product(promo_valid_until="2026-10-07"),
            "promo_price_eur and promo_valid_until must be set together",
        ),
        (
            "promotion without regular price",
            _break_first_product(promo_price_eur=1.29, promo_valid_until="2026-10-07"),
            "a promotion needs regular_price_eur",
        ),
        (
            "promo price not below the regular price",
            _milk_promo("2026-10-07", regular_price_eur=1.29),
            "promo_price_eur must be below regular_price_eur",
        ),
        (
            "promo price with 3 decimals",
            _milk_promo("2026-10-07", promo_price_eur=1.299),
            "decimal",
        ),
        ("promo end date not ISO", _milk_promo("07.10.2026"), "promo_valid_until"),
        (
            "promotion ended before it was seen",
            _milk_promo("2026-09-30"),
            "promo_valid_until must not be before price_date",
        ),
        (
            "price neither regular nor promo",
            _break_first_product(regular_price_eur=1.49),
            "price_eur must be regular_price_eur or promo_price_eur",
        ),
        (
            "ended promotion still priced as promo",
            _milk_promo("2026-09-25", price_date="2026-09-20"),
            "price_eur must be the price on the catalog's price_date 2026-10-01 "
            "(regular price once a promotion has ended): at-lidl-milk-1l",
        ),
        (
            "running promotion priced as regular",
            _milk_promo("2026-10-07", price_eur=1.49),
            "price_eur must be the price on the catalog's price_date 2026-10-01",
        ),
    ],
)
def test_invalid_concept_or_promotion_fails_fast(
    write_catalog: Callable[[dict[str, Any]], Path],
    case: str,
    data: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(CatalogLoadError, match="invalid catalog") as info:
        load_catalog(write_catalog(data))

    assert message in str(info.value), case


def test_catalogs_without_promotion_fields_still_load(catalog: ProductCatalog) -> None:
    milk = catalog.get(AT_MILK)  # the fixture predates promotions

    assert milk is not None
    assert (milk.regular_price_eur, milk.promo_price_eur, milk.promo_valid_until) == (None,) * 3
    assert milk.price_on(date(2030, 1, 1)) == milk.price_eur == Decimal("1.29")


def test_a_running_promotion_is_the_price() -> None:
    data = _milk_promo("2026-10-07")
    catalog = ProductCatalog(Catalog.model_validate(data), today=lambda: date(2026, 10, 7))

    milk = catalog.get(AT_MILK)
    assert milk is not None
    assert (milk.price_eur, milk.regular_price_eur, milk.promo_price_eur) == (
        Decimal("1.29"),
        Decimal("1.49"),
        Decimal("1.29"),
    )
    assert milk in catalog.candidates("AT", ["Lidl"], [])


def test_an_ended_promotion_costs_the_regular_price_without_a_reload(
    caplog: pytest.LogCaptureFixture,
) -> None:
    today = date(2026, 10, 7)
    catalog = ProductCatalog(Catalog.model_validate(_milk_promo("2026-10-07")), lambda: today)
    assert (milk := catalog.get(AT_MILK)) is not None and milk.price_eur == Decimal("1.29")

    today = date(2026, 10, 8)
    with caplog.at_level(logging.INFO, logger="app.services.catalog"):
        milk = catalog.get(AT_MILK)

    assert milk is not None and milk.price_eur == Decimal("1.49")
    assert milk.promo_valid_until == date(2026, 10, 7)  # still recorded
    [candidate] = [p for p in catalog.candidates("AT", ["Lidl"], []) if p.id == AT_MILK]
    assert candidate.price_eur == Decimal("1.49")
    assert catalog.catalog.products[0].price_eur == Decimal("1.29")  # as in the file
    assert "Promotions ended by 2026-10-08" in caplog.text


def test_a_clock_behind_the_catalog_date_cannot_bring_back_a_promotion() -> None:
    # Ended before the catalog's price_date (2026-10-01), so the file has the regular price.
    data = _milk_promo("2026-09-25", price_date="2026-09-20", price_eur=1.49)
    catalog = ProductCatalog(Catalog.model_validate(data), today=lambda: date(2026, 9, 21))

    milk = catalog.get(AT_MILK)
    assert milk is not None and milk.price_eur == Decimal("1.49")


@pytest.mark.parametrize(
    ("until", "price", "total"),
    [("2099-12-31", 1.29, 8.85), ("2026-10-01", 1.49, 9.25)],
    ids=["running", "ended"],
)
def test_plans_are_priced_with_todays_price(
    write_catalog: Callable[[dict[str, Any]], Path],
    make_client: Callable[..., TestClient],
    fake_llm: FakeOpenAI,
    until: str,
    price: float,
    total: float,
) -> None:
    """pricing and planner read price_eur, so they get the promo price only while it runs."""
    client = make_client(catalog_path=write_catalog(_milk_promo(until)))
    fake_llm.queue_plan(make_plan())  # milk x2, apples x2 (3.98), rice x1 (2.29)

    response = client.post("/generate", json=BODY)

    assert response.status_code == 200
    body = response.json()
    assert (body["items"][0]["product_id"], body["items"][0]["unit_price"]) == (MILK, price)
    assert body["total"] == total
    assert f"| €{price:.2f} | Lidl |" in fake_llm.messages()[-1]["content"]
