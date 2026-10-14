import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.catalog import NON_FOOD_CATEGORIES
from app.services.catalog import CatalogLoadError, ProductCatalog, load_catalog
from tests.conftest import make_settings

FIXTURE = Path(__file__).parent / "fixtures" / "catalog_small.json"
PLACEHOLDER = Path(__file__).parents[1] / "app" / "data" / "catalog.json"


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


def test_placeholder_catalog_is_valid_and_empty() -> None:
    assert len(load_catalog(PLACEHOLDER)) == 0


def test_app_starts_with_placeholder_catalog() -> None:
    app = create_app(make_settings(catalog_path=PLACEHOLDER))

    assert TestClient(app).get("/health").status_code == 200
    assert len(app.state.catalog) == 0


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
