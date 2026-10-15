"""Build app/data/catalog.json from the human-editable CSV source.

    cd backend
    python -m scripts.build_catalog            # data_src/catalog_at.csv -> app/data/catalog.json
    python -m scripts.build_catalog --check    # validate only, write nothing

Nutrition in the CSV is per 100 g or 100 ml; the catalog stores it per pack. Products sold
by kg or l are converted with their pack size (1 ml counted as 1 g). Products sold by pcs or
pack need `net_weight_g` (contents of one pack in grams) unless they are non-food.

Every row is validated with the app's Pydantic schema; any error stops the build.
"""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, get_args

from pydantic import ValidationError

from app.schemas.catalog import NON_FOOD_CATEGORIES, Catalog, DietTag, Product

BACKEND = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = BACKEND / "data_src" / "catalog_at.csv"
DEFAULT_OUTPUT = BACKEND / "app" / "data" / "catalog.json"
COUNTRY = "AT"

COLUMNS = [
    "id",
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
    "kcal_100",
    "protein_100",
    "fat_100",
    "carbs_100",
    "diet_tags",
    "source_url",
    "price_date",
    "verified",
]
NUTRIENTS = {
    "kcal": "kcal_100",
    "protein_g": "protein_100",
    "fat_g": "fat_100",
    "carbs_g": "carbs_100",
}


class BuildError(Exception):
    pass


def pack_grams(row: dict[str, str]) -> float:
    """Contents of one pack in g (or ml), for converting nutrition per 100 g to per pack."""
    if row["unit"] in ("kg", "l"):
        return float(row["pack_size"]) * 1000
    if not row["net_weight_g"]:
        raise BuildError(f"net_weight_g is required for a food product sold by {row['unit']}")
    return float(row["net_weight_g"])


def to_product(row: dict[str, str]) -> dict[str, Any]:
    if row["verified"] not in ("yes", "no"):
        raise BuildError(f"verified must be yes or no, not {row['verified']!r}")
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
        "country": COUNTRY,
        "store": row["store"],
        "name": {"en": row["name_en"], "uk": row["name_uk"], "de": row["name_de"]},
        "category": row["category"],
        "unit": row["unit"],
        "pack_size": float(row["pack_size"]),
        "portion_unit": row["portion_unit"] or None,
        "price_eur": row["price_eur"],
        **nutrition,
        "diet_tags": [tag for tag in row["diet_tags"].split(";") if tag],
        "source_url": row["source_url"],
        "price_date": row["price_date"],
    }


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
    for line, row in enumerate(rows, start=2):  # line 1 is the header
        try:
            products.append(Product.model_validate(to_product(row)))
        except (BuildError, ValidationError, ValueError) as e:
            errors.append(f"{source.name}:{line} ({row.get('id') or '?'}): {e}")
    if errors:
        raise BuildError("\n".join(errors))
    if not products:
        raise BuildError("no products")
    price_date = max(p.price_date for p in products)
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
    unverified = sum(1 for row in rows if row["verified"] != "yes")
    lines.append(f"Unverified rows: {unverified}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="validate only, don't write")
    args = parser.parse_args(argv)
    try:
        catalog, rows = build(args.source)
    except (BuildError, OSError) as e:
        print(f"Catalog build failed:\n{e}", file=sys.stderr)
        return 1
    print(report(catalog, rows))
    if not args.check:
        data = catalog.model_dump(mode="json")
        for product in data["products"]:
            product["price_eur"] = float(product["price_eur"])  # a number, like the fixture
        args.output.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
