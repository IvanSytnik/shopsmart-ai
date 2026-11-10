"""Build app/data/catalog.json from the human-editable CSV source.

    cd backend
    python scripts/build_catalog.py            # data_src/catalog_at.csv -> app/data/catalog.json
    python scripts/build_catalog.py --check    # validate, and fail if catalog.json is stale

`python -m scripts.build_catalog` works too.

Nutrition in the CSV is per 100 g or 100 ml; the catalog stores it per pack. Products sold
by kg or l are converted with their pack size (1 ml counted as 1 g). Products sold by pcs or
pack need `net_weight_g` (contents of one pack in grams) unless they are non-food.

`price_eur` is the regular shelf price. A promotion adds `promo_price_eur` and
`promo_valid_until` (its last day, YYYY-MM-DD). In catalog.json, `price_eur` is the price
every plan uses: the promo price if the promotion still runs on the catalog's price_date
(the latest row date), the regular price otherwise; the CSV price goes to
`regular_price_eur`.

`concept_id` names the kind of product, without its pack size (`milk_whole`); products a
shopper would buy in place of each other share it and must have the same unit and category,
so prices compare per kg, l or piece. Diet tags may differ: diets filter within a concept.

Every row is validated with the app's Pydantic schema; any error stops the build.
"""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, get_args

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:  # run as a file (`python scripts/build_catalog.py`)
    sys.path.insert(0, str(BACKEND))

from pydantic import ValidationError  # noqa: E402

from app.schemas.catalog import (  # noqa: E402
    NON_FOOD_CATEGORIES,
    Catalog,
    DietTag,
    Product,
    Unit,
)

DEFAULT_SOURCE = BACKEND / "data_src" / "catalog_at.csv"
DEFAULT_OUTPUT = BACKEND / "app" / "data" / "catalog.json"
COUNTRY = "AT"

COLUMNS = [
    "id",
    "concept_id",
    "store",
    "category",
    "name_en",
    "name_uk",
    "name_de",
    "unit",
    "pack_size",
    "net_weight_g",
    "portion_unit",
    "price_eur",
    "promo_price_eur",
    "promo_valid_until",
    "kcal_100",
    "protein_100",
    "fat_100",
    "carbs_100",
    "diet_tags",
    "source_url",
    "price_date",
    "verified",
]
MONEY_FIELDS = ("price_eur", "regular_price_eur", "promo_price_eur")
NUTRIENTS = {
    "kcal": "kcal_100",
    "protein_g": "protein_100",
    "fat_g": "fat_100",
    "carbs_g": "carbs_100",
}


class BuildError(Exception):
    pass


# A vegan product has no animal ingredients, so it is vegetarian and lactose-free too. The
# diet filter needs every chosen tag, so a missing one hides the product from those diets.
VEGAN_IMPLIES = ("vegetarian", "lactose_free")


def pack_grams(row: dict[str, str]) -> float:
    """Contents of one pack in g (or ml), for converting nutrition per 100 g to per pack."""
    if row["unit"] in ("kg", "l"):
        return float(row["pack_size"]) * 1000
    if not row["net_weight_g"]:
        raise BuildError(f"net_weight_g is required for a food product sold by {row['unit']}")
    return float(row["net_weight_g"])


def to_product(row: dict[str, str]) -> dict[str, Any]:
    if row["unit"] not in get_args(Unit):
        raise BuildError(f"unknown unit {row['unit']!r}")
    if row["verified"] not in ("yes", "no"):
        raise BuildError(f"verified must be yes or no, not {row['verified']!r}")
    tags = [tag for tag in row["diet_tags"].split(";") if tag]
    missing = [tag for tag in VEGAN_IMPLIES if "vegan" in tags and tag not in tags]
    if missing:
        raise BuildError(f"a vegan row must also be tagged {', '.join(missing)}")
    values = [row[column] for column in NUTRIENTS.values()]
    nutrition: dict[str, float | None]
    if all(values) and row["category"] not in NON_FOOD_CATEGORIES:
        factor = pack_grams(row) / 100
        nutrition = {key: round(float(row[col]) * factor, 1) for key, col in NUTRIENTS.items()}
    elif not any(values):
        nutrition = dict.fromkeys(NUTRIENTS)
    else:
        raise BuildError("nutrition must be all set (food) or all empty (non-food)")
    return {
        "id": row["id"],
        "concept_id": row["concept_id"],
        "country": COUNTRY,
        "store": row["store"],
        "name": {"en": row["name_en"], "uk": row["name_uk"], "de": row["name_de"]},
        "category": row["category"],
        "unit": row["unit"],
        "pack_size": float(row["pack_size"]),
        "portion_unit": row["portion_unit"] or None,
        # As of the row's own price_date, when a promotion runs; build() reprices every
        # product as of the catalog's price_date.
        "price_eur": row["promo_price_eur"] or row["price_eur"],
        "regular_price_eur": row["price_eur"],
        "promo_price_eur": row["promo_price_eur"] or None,
        "promo_valid_until": row["promo_valid_until"] or None,
        **nutrition,
        "diet_tags": tags,
        "source_url": row["source_url"],
        "price_date": row["price_date"],
    }


def concept_conflict(product: Product, other: Product) -> str | None:
    """Products sharing a concept_id are compared by price per unit, so they must be sold in
    the same unit and category. Their diet tags may differ (lactose-free and regular butter)."""
    differ = [
        field
        for field, a, b in (
            ("unit", product.unit, other.unit),
            ("category", product.category, other.category),
        )
        if a != b
    ]
    if not differ:
        return None
    return f"concept {product.concept_id} differs from {other.id} in {', '.join(differ)}"


def read_rows(source: Path) -> list[dict[str, str]]:
    with source.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise BuildError(f"columns must be exactly: {', '.join(COLUMNS)}")
        return [{k: (v or "").strip() for k, v in row.items()} for row in reader]


def build(source: Path) -> tuple[Catalog, list[dict[str, str]]]:
    rows = read_rows(source)
    products = []
    errors = []
    by_concept: dict[str, Product] = {}
    for line, row in enumerate(rows, start=2):  # line 1 is the header
        try:
            product = Product.model_validate(to_product(row))
            conflict = concept_conflict(product, by_concept.setdefault(product.concept_id, product))
            if conflict:
                raise BuildError(conflict)
            products.append(product)
        except (BuildError, ValidationError, ValueError) as e:
            errors.append(f"{source.name}:{line} ({row.get('id') or '?'}): {e}")
    if errors:
        raise BuildError("\n".join(errors))
    if not products:
        raise BuildError("no products")
    price_date = max(p.price_date for p in products)
    products = [p.priced_on(price_date) for p in products]  # ended promotions: regular price
    try:
        catalog = Catalog(
            version=f"at-{price_date.isoformat()}", price_date=price_date, products=products
        )
    except ValidationError as e:
        raise BuildError(str(e)) from e
    return catalog, rows


def report(catalog: Catalog, rows: list[dict[str, str]]) -> str:
    food = [p for p in catalog.products if p.category not in NON_FOOD_CATEGORIES]
    lines = [f"{len(catalog.products)} products ({len(food)} food), version {catalog.version}"]
    stores = Counter(p.store for p in catalog.products)
    food_stores = Counter(p.store for p in food)
    lines.append(
        "Per store (food/all): "
        + ", ".join(f"{s} {food_stores[s]}/{n}" for s, n in sorted(stores.items()))
    )
    for store in sorted(stores):
        categories = Counter(p.category for p in catalog.products if p.store == store)
        lines.append(f"  {store}: " + ", ".join(f"{c} {n}" for c, n in sorted(categories.items())))
    diets = {tag: sum(1 for p in food if tag in p.diet_tags) for tag in get_args(DietTag)}
    lines.append("Food per diet tag: " + ", ".join(f"{t} {n}" for t, n in diets.items()))
    stores_by_concept: defaultdict[str, set[str]] = defaultdict(set)
    for p in catalog.products:
        stores_by_concept[p.concept_id].add(p.store)
    shared = sum(1 for names in stores_by_concept.values() if len(names) > 1)
    lines.append(f"Concepts: {len(stores_by_concept)}, {shared} in more than one store")
    promos = [p for p in catalog.products if p.promo_valid_until is not None]
    ended = [p.id for p in promos if not p.promo_runs_on(catalog.price_date)]
    lines.append(
        f"Promotions running on {catalog.price_date}: {len(promos) - len(ended)}"
        + (f"; ended, regular price used: {', '.join(ended)}" if ended else "")
    )
    unverified = sum(1 for row in rows if row["verified"] != "yes")
    lines.append(f"Unverified rows: {unverified}")
    return "\n".join(lines)


def render(catalog: Catalog) -> str:
    data = catalog.model_dump(mode="json")
    for product in data["products"]:
        for field in MONEY_FIELDS:  # numbers, like the fixture
            if product[field] is not None:
                product[field] = float(product[field])
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate, don't write; fail if --output differs from a fresh build",
    )
    args = parser.parse_args(argv)
    try:
        catalog, rows = build(args.source)
    except (BuildError, OSError) as e:
        print(f"Catalog build failed:\n{e}", file=sys.stderr)
        return 1
    print(report(catalog, rows))
    text = render(catalog)
    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.exists() else None
        if current != text:
            print(
                f"{args.output} is out of date: run `python scripts/build_catalog.py`",
                file=sys.stderr,
            )
            return 1
        print(f"{args.output} is up to date")
        return 0
    args.output.write_text(text, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
