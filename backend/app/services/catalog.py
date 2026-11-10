"""Loads the price catalog once at startup and answers lookups against it."""

import logging
from collections.abc import Callable, Collection
from datetime import date
from pathlib import Path
from typing import get_args

from pydantic import ValidationError

from app.schemas.catalog import NON_FOOD_CATEGORIES, Catalog, Country, DietTag, Product
from app.schemas.compare import ConceptSummary

logger = logging.getLogger(__name__)


class CatalogLoadError(Exception):
    """The catalog file is missing, not JSON, or fails validation."""


class ProductCatalog:
    """Lookups return each product with `price_eur` as of today: once a promotion has ended,
    its regular price, without rebuilding or reloading the catalog."""

    def __init__(self, catalog: Catalog, today: Callable[[], date] = date.today) -> None:
        self.catalog = catalog  # as in the file: prices as of catalog.price_date
        self._today = today
        self._as_of = catalog.price_date
        self._by_id = {product.id: product for product in catalog.products}
        self._ids_by_concept: dict[str, list[str]] = {}
        for product in catalog.products:
            self._ids_by_concept.setdefault(product.concept_id, []).append(product.id)
        self._concept_names = {c.concept_id: c.name for c in catalog.concepts}

    def _current(self) -> dict[str, Product]:
        # Never before the catalog's own date, so an ended promotion can't come back.
        as_of = max(self._today(), self.catalog.price_date)
        if as_of != self._as_of:
            by_id = {product.id: product.priced_on(as_of) for product in self.catalog.products}
            ended = [i for i, p in by_id.items() if p.price_eur != self._by_id[i].price_eur]
            if ended:
                logger.info("Promotions ended by %s, regular prices apply: %s", as_of, ended)
            self._by_id = by_id
            self._as_of = as_of
        return self._by_id

    def __len__(self) -> int:
        return len(self._by_id)

    def get(self, product_id: str) -> Product | None:
        return self._current().get(product_id)

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
            for product in self._current().values()
            if product.country == country
            and product.store in stores
            and _fits_diets(product, required)
        ]

    def products_for_concept(
        self,
        concept_id: str,
        country: Country,
        stores: Collection[str] | None = None,
        diets: Collection[DietTag] = (),
    ) -> list[Product]:
        """Products of `concept_id` sold in `country` (at one of `stores`, if given) that fit
        every diet in `diets`, in catalog order. Empty for an unknown concept."""
        current = self._current()
        required = set(diets)
        return [
            product
            for product_id in self._ids_by_concept.get(concept_id, [])
            if (product := current[product_id]).country == country
            and (stores is None or product.store in stores)
            and _fits_diets(product, required)
        ]

    def reference_pack_size(self, concept_id: str, country: Country) -> float | None:
        """What quantity 1 of a concept means in a comparison: its smallest pack in `country`,
        in the concept's unit; None if `country` doesn't sell it."""
        sizes = [p.pack_size for p in self.products_for_concept(concept_id, country)]
        return min(sizes, default=None)

    def concepts(self, country: Country) -> list[ConceptSummary]:
        """Every concept sold in `country`, sorted by id."""
        summaries = []
        for concept_id in sorted(self._ids_by_concept):
            products = self.products_for_concept(concept_id, country)
            if not products:
                continue
            first = products[0]  # the catalog build requires one unit and category per concept
            summaries.append(
                ConceptSummary(
                    concept_id=concept_id,
                    name=self._concept_names[concept_id],  # the catalog names every concept
                    names=list(dict.fromkeys(p.name for p in products)),
                    category=first.category,
                    unit=first.unit,
                    stores=sorted({p.store for p in products}),
                    reference_pack_size=min(p.pack_size for p in products),
                )
            )
        return summaries


def _fits_diets(product: Product, diets: set[DietTag]) -> bool:
    """Diets only filter food: cleaning and hygiene products fit every diet."""
    return product.category in NON_FOOD_CATEGORIES or diets <= set(product.diet_tags)


def load_catalog(path: Path) -> ProductCatalog:
    """Read and validate the catalog; raises `CatalogLoadError` so startup fails fast."""
    try:
        catalog = Catalog.model_validate_json(path.read_bytes())
    except OSError as e:
        raise CatalogLoadError(f"cannot read catalog {path}: {e}") from e
    except ValidationError as e:
        raise CatalogLoadError(f"invalid catalog {path}:\n{e}") from e
    logger.info(
        "Loaded catalog %s: %d products (%d with a promotion), prices as of %s",
        catalog.version,
        len(catalog.products),
        sum(1 for p in catalog.products if p.promo_valid_until is not None),
        catalog.price_date,
    )
    return ProductCatalog(catalog)
