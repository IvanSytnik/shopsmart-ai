"""Coverage of the real Austrian catalog (app/data/catalog.json and its CSV source)."""

import csv
import json
from itertools import combinations
from pathlib import Path
from typing import get_args
from urllib.parse import urlparse

import pytest

from app.schemas.catalog import NON_FOOD_CATEGORIES, DietTag
from app.services.catalog import load_catalog
from scripts.build_catalog import DEFAULT_SOURCE, BuildError, build, main
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


def test_build_requires_net_weight_for_food_sold_by_pieces(tmp_path: Path) -> None:
    eggs = next(row for row in csv_rows() if row["id"] == "at-billa-eggs-m-10")
    source = write_csv(tmp_path / "eggs.csv", [{**eggs, "net_weight_g": ""}])

    with pytest.raises(BuildError, match="net_weight_g is required"):
        build(source)


def test_main_check_mode_writes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "catalog.json"

    assert main(["--check", "--output", str(output)]) == 0
    assert not output.exists()
    assert "Unverified rows:" in capsys.readouterr().out
    bad = write_csv(tmp_path / "bad.csv", [{**csv_rows()[0], "price_eur": "x"}])
    assert main(["--source", str(bad), "--output", str(output)]) == 1
    assert not output.exists()
