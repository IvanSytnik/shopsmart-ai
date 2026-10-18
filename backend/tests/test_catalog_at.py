"""Coverage of the real Austrian catalog (app/data/catalog.json and its CSV source)."""

import csv
import json
import subprocess
import sys
from collections.abc import Callable
from itertools import combinations
from pathlib import Path
from typing import get_args
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from app.schemas.catalog import NON_FOOD_CATEGORIES, DietTag
from app.services.catalog import load_catalog
from scripts.build_catalog import BACKEND, DEFAULT_SOURCE, BuildError, build, main
from tests.conftest import FakeOpenAI
from tests.test_catalog import PRODUCTION_CATALOG

CATALOG = load_catalog(PRODUCTION_CATALOG)
AT_STORES = CATALOG.stores_by_country()["AT"]
STORE_DOMAINS = {
    "Hofer": "www.hofer.at",
    "Billa": "shop.billa.at",
    "Spar": "www.spar.at",
    "Lidl": "www.lidl.at",
}
MIN_FOOD_PER_STORE = 25
MIN_CANDIDATES = 12  # app.services.planner.MIN_FOOD_CANDIDATES
MAX_PAIR_CANDIDATES = 100  # keeps the LLM schema enum within its limit


def csv_rows() -> list[dict[str, str]]:
    with DEFAULT_SOURCE.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def food_count(stores: list[str], diets: list[DietTag]) -> int:
    candidates = CATALOG.candidates("AT", stores, diets)
    return sum(1 for p in candidates if p.category not in NON_FOOD_CATEGORIES)


def test_only_known_austrian_stores() -> None:
    assert len(AT_STORES) >= 2
    assert set(AT_STORES) <= set(STORE_DOMAINS)
    assert CATALOG.stores_by_country()["DE"] == []


@pytest.mark.parametrize("store", AT_STORES)
def test_each_store_has_enough_food(store: str) -> None:
    assert food_count([store], []) >= MIN_FOOD_PER_STORE


@pytest.mark.parametrize("diet", [None, *get_args(DietTag)])
@pytest.mark.parametrize("pair", list(combinations(AT_STORES, 2)))
def test_every_store_pair_has_enough_candidates_per_diet(
    pair: tuple[str, str], diet: DietTag | None
) -> None:
    assert food_count(list(pair), [diet] if diet else []) >= MIN_CANDIDATES


# Single stores that can't offer enough food for a diet. Requests for them get
# 422 not_enough_products; update this when the catalog grows.
SHORT_SINGLE_STORE_DIETS = {("Hofer", "vegan")}


def test_single_store_diet_gaps_are_the_known_ones() -> None:
    short = {
        (store, diet)
        for store in AT_STORES
        for diet in get_args(DietTag)
        if food_count([store], [diet]) < MIN_CANDIDATES
    }
    assert short == SHORT_SINGLE_STORE_DIETS
    assert all(food_count([store], []) >= MIN_CANDIDATES for store in AT_STORES)


@pytest.mark.parametrize("diet", get_args(DietTag))
@pytest.mark.parametrize("store", AT_STORES)
def test_single_store_with_a_diet_is_planned_or_rejected_clearly(
    store: str, diet: DietTag, make_client: Callable[..., TestClient], fake_llm: FakeOpenAI
) -> None:
    client = make_client(catalog_path=PRODUCTION_CATALOG)
    body = {"country": "AT", "supermarkets": [store], "budget": 50, "diets": [diet]}
    if (store, diet) in SHORT_SINGLE_STORE_DIETS:
        response = client.post("/generate", json=body)

        assert response.status_code == 422
        assert response.json()["code"] == "not_enough_products"
        assert fake_llm.calls == 0
    else:
        assert food_count([store], [diet]) >= MIN_CANDIDATES


@pytest.mark.parametrize("pair", list(combinations(AT_STORES, 2)))
def test_store_pairs_stay_within_the_enum_limit(pair: tuple[str, str]) -> None:
    assert len(CATALOG.candidates("AT", list(pair), [])) <= MAX_PAIR_CANDIDATES


def test_csv_has_no_duplicate_ids() -> None:
    ids = [row["id"] for row in csv_rows()]
    assert len(ids) == len(set(ids))


def test_every_row_has_a_source_url_on_its_store_site() -> None:
    for row in csv_rows():
        url = urlparse(row["source_url"])
        assert url.scheme == "https", row["id"]
        assert url.netloc == STORE_DOMAINS[row["store"]], row["id"]
        assert row["price_date"], row["id"]
        assert row["verified"] in ("yes", "no"), row["id"]


def test_catalog_json_is_built_from_the_csv() -> None:
    catalog, _ = build(DEFAULT_SOURCE)
    on_disk = json.loads(PRODUCTION_CATALOG.read_text(encoding="utf-8"))

    assert [p.id for p in catalog.products] == [p["id"] for p in on_disk["products"]]
    assert catalog.version == on_disk["version"]
    assert catalog.products == CATALOG.catalog.products


def test_nutrition_is_converted_to_per_pack() -> None:
    milk = CATALOG.get("at-hofer-whole-milk-1l")  # 64 kcal / 100 ml, 1 l
    eggs = CATALOG.get("at-billa-eggs-m-10")  # 140 kcal / 100 g, 530 g net
    assert milk is not None and (milk.kcal, milk.protein_g) == (640, 33)
    assert eggs is not None and eggs.kcal == 742


# Vegan breads and bakery: lactose-free users lost them while the tag was missing.
VEGAN_BREADS = {
    "at-hofer-organic-rye-bread-500g",
    "at-hofer-crust-bread-750g",
    "at-hofer-kaiser-rolls-420g",
    "at-hofer-rye-crispbread-250g",
    "at-hofer-mini-baguettes-300g",
    "at-hofer-vegan-wholegrain-toast-500g",
    "at-hofer-rye-farmhouse-slices-500g",
    "at-billa-bake-off-rolls-300g",
    "at-billa-pretzel-sticks-250g",
}


def test_every_vegan_product_is_vegetarian_and_lactose_free() -> None:
    for product in CATALOG.catalog.products:
        if "vegan" in product.diet_tags:
            assert {"vegetarian", "lactose_free"} <= set(product.diet_tags), product.id


def test_lactose_free_hofer_includes_the_vegan_breads() -> None:
    candidates = {p.id for p in CATALOG.candidates("AT", ["Hofer"], ["lactose_free"])}

    assert {i for i in VEGAN_BREADS if i.startswith("at-hofer-")} <= candidates
    assert len(candidates) == 20


# --- the build script -----------------------------------------------------------


def write_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"price_eur": "1.299"}, "decimal places"),
        ({"unit": "box"}, "unknown unit 'box'"),
        ({"kcal_100": ""}, "all set (food) or all empty"),
        ({"verified": "maybe"}, "verified must be yes or no"),
        ({"portion_unit": "pcs"}, "portion_unit 'pcs' doesn't fit unit 'kg'"),  # Gouda
    ],
)
def test_build_fails_on_a_bad_row(tmp_path: Path, change: dict[str, str], message: str) -> None:
    rows = csv_rows()[:2]
    rows[1] = {**rows[1], **change}
    source = write_csv(tmp_path / "bad.csv", rows)

    with pytest.raises(BuildError, match=r"bad\.csv:3") as info:
        build(source)
    assert message in str(info.value)


@pytest.mark.parametrize(
    ("tags", "missing"),
    [
        ("vegan;vegetarian", "lactose_free"),
        ("vegan;lactose_free", "vegetarian"),
        ("vegan", "vegetarian, lactose_free"),
    ],
)
def test_build_fails_on_a_vegan_row_without_the_implied_tags(
    tmp_path: Path, tags: str, missing: str
) -> None:
    rows = [row for row in csv_rows() if row["id"] in VEGAN_BREADS][:2]
    rows = [{**row, "diet_tags": tags} for row in rows]
    source = write_csv(tmp_path / "vegan.csv", rows)

    with pytest.raises(BuildError) as info:
        build(source)
    for line, row in enumerate(rows, start=2):  # every violation, with its line and id
        assert f"vegan.csv:{line} ({row['id']}): a vegan row must also be tagged {missing}" in str(
            info.value
        )


def test_build_fails_on_the_untagged_vegan_rows_in_check_mode(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rows = [
        {**row, "diet_tags": "vegan;vegetarian"} if row["id"] in VEGAN_BREADS else row
        for row in csv_rows()
    ]
    source = write_csv(tmp_path / "catalog_at.csv", rows)

    assert main(["--source", str(source), "--output", str(PRODUCTION_CATALOG), "--check"]) == 1
    errors = capsys.readouterr().err
    assert "Catalog build failed" in errors
    assert all(product_id in errors for product_id in VEGAN_BREADS)


def test_build_requires_net_weight_for_food_sold_by_pieces(tmp_path: Path) -> None:
    eggs = next(row for row in csv_rows() if row["id"] == "at-billa-eggs-m-10")
    source = write_csv(tmp_path / "eggs.csv", [{**eggs, "net_weight_g": ""}])

    with pytest.raises(BuildError, match="net_weight_g is required"):
        build(source)


def test_check_mode_writes_nothing_and_detects_a_stale_catalog(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--check"]) == 0  # the committed catalog.json is up to date
    assert "Unverified rows:" in capsys.readouterr().out

    output = tmp_path / "catalog.json"
    assert main(["--check", "--output", str(output)]) == 1  # missing
    assert not output.exists()
    assert main(["--output", str(output)]) == 0
    assert main(["--check", "--output", str(output)]) == 0
    output.write_text(output.read_text().replace('"1.32"', '"1.33"').replace("1.32", "1.33"))
    assert main(["--check", "--output", str(output)]) == 1
    assert "out of date" in capsys.readouterr().err


def test_build_failure_writes_nothing(tmp_path: Path) -> None:
    output = tmp_path / "catalog.json"
    bad = write_csv(tmp_path / "bad.csv", [{**csv_rows()[0], "price_eur": "x"}])

    assert main(["--source", str(bad), "--output", str(output)]) == 1
    assert not output.exists()


@pytest.mark.parametrize(
    "command",
    [
        [sys.executable, "scripts/build_catalog.py", "--check"],
        [sys.executable, "-m", "scripts.build_catalog", "--check"],
    ],
    ids=["as-file", "as-module"],
)
def test_script_runs_from_the_backend_directory(command: list[str]) -> None:
    result = subprocess.run(
        command, cwd=BACKEND, capture_output=True, text=True, check=False, timeout=60
    )

    assert result.returncode == 0, result.stderr
    assert "is up to date" in result.stdout
