"""Loads the price catalog once at startup and answers lookups against it."""

import logging
from collections.abc import Collection
from pathlib import Path
from typing import get_args

from pydantic import ValidationError

from app.schemas.catalog import NON_FOOD_CATEGORIES, Catalog, Country, DietTag, Product

logger = logging.getLogger(__name__)


class CatalogLoadError(Exception):
    """The catalog file is missing, not JSON, or fails validation."""


class ProductCatalog:
    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog
        self._by_id = {product.id: product for product in catalog.products}

    def __len__(self) -> int:
        return len(self._by_id)

    def get(self, product_id: str) -> Product | None:
        return self._by_id.get(product_id)

    def stores_by_country(self) -> dict[Country, list[str]]:
        """Every country, each with its stores sorted by name (empty if it has none)."""
        stores: dict[Country, set[str]] = {country: set() for country in get_args(Country)}
        for product in self.catalog.products:
            stores[product.country].add(product.store)
        return {country: sorted(names) for country, names in stores.items()}

    def candidates(
        self, country: Country, stores: Collection[str], diets: Collection[DietTag]
    ) -> list[Product]:
        """Products sold in `country` at one of `stores` that fit every diet in `diets`.

        Diets only filter food: cleaning and hygiene products are always kept.
        """
        required = set(diets)
        return [
            product
            for product in self.catalog.products
            if product.country == country
            and product.store in stores
            and (product.category in NON_FOOD_CATEGORIES or required <= set(product.diet_tags))
        ]


def load_catalog(path: Path) -> ProductCatalog:
    """Read and validate the catalog; raises `CatalogLoadError` so startup fails fast."""
    try:
        catalog = Catalog.model_validate_json(path.read_bytes())
    except OSError as e:
        raise CatalogLoadError(f"cannot read catalog {path}: {e}") from e
    except ValidationError as e:
        raise CatalogLoadError(f"invalid catalog {path}:\n{e}") from e
    logger.info(
        "Loaded catalog %s: %d products, prices as of %s",
        catalog.version,
        len(catalog.products),
        catalog.price_date,
    )
    return ProductCatalog(catalog)
