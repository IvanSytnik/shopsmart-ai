"""Prices a shopping list of concepts at each chosen store; deterministic, no LLM.

Quantity: an item's `quantity` counts the concept's reference pack, its smallest pack in the
country (`reference_pack_size` in GET /api/catalog/concepts). Each store buys the fewest
whole packs that hold at least that much, so every basket has at least the requested amount
and totals compare like for like: 2 x yogurt (smallest pack 250 g) is 2 x 250 g at one store
and 1 x 500 g at another. No store buys more than `quantity` packs.

Choice: within a store, and across stores for the split basket, the lowest line total for
that amount wins. Ties go to the lower price per base unit (1 kg, 1 l, 1 piece or 1 pack,
the product's `unit`), then to the store name and product id. Prices are today's: the promo
price while a promotion runs (see ProductCatalog).

Savings compare the same items: a store that misses an item is compared with what the split
basket pays for the items it has.
"""

import logging
from collections import defaultdict
from collections.abc import Iterable
from decimal import Decimal
from math import ceil

from app.schemas.catalog import Product
from app.schemas.compare import (
    CompareRequest,
    CompareResponse,
    MatchedStoreItem,
    SplitBasket,
    SplitStoreGroup,
    StoreComparison,
)
from app.services.catalog import ProductCatalog
from app.services.pricing import round_money

logger = logging.getLogger(__name__)

ZERO = Decimal("0")


def _pack_size(pack_size: float) -> Decimal:
    return Decimal(str(pack_size))  # exact: 3 x 0.1 kg is 0.3 kg, not 0.30000000000000004


def _per_unit(item: MatchedStoreItem) -> Decimal:
    return item.price_eur / _pack_size(item.pack_size)


def _match(product: Product, amount: Decimal) -> MatchedStoreItem:
    """`product` bought in the fewest whole packs that hold `amount` (in its unit)."""
    packs = max(1, ceil(amount / _pack_size(product.pack_size)))
    # Promo prices are below regular ones, so price_eur is the promo price only while it runs.
    promo = product.promo_price_eur
    promo_runs = promo is not None and product.price_eur == promo
    regular = product.regular_price_eur  # None in catalogs from before promotions
    return MatchedStoreItem(
        concept_id=product.concept_id,
        product_id=product.id,
        names=product.name,
        store=product.store,
        packs_needed=packs,
        pack_size=product.pack_size,
        unit=product.unit,
        price_eur=product.price_eur,
        regular_price_eur=product.price_eur if regular is None else regular,
        promo_price_eur=promo if promo_runs else None,
        promo_valid_until=product.promo_valid_until if promo_runs else None,
        line_total_eur=round_money(product.price_eur * packs),
        price_per_base_unit_eur=round_money(product.price_eur / _pack_size(product.pack_size)),
    )


def _cheapest(items: Iterable[MatchedStoreItem]) -> MatchedStoreItem | None:
    return min(
        items,
        key=lambda i: (i.line_total_eur, _per_unit(i), i.store, i.product_id),
        default=None,
    )


def _total(items: Iterable[MatchedStoreItem]) -> Decimal:
    return sum((item.line_total_eur for item in items), ZERO)


def _promo_savings(items: Iterable[MatchedStoreItem]) -> Decimal:
    return sum(
        ((item.regular_price_eur - item.price_eur) * item.packs_needed for item in items), ZERO
    )


def _store_comparison(
    catalog: ProductCatalog, request: CompareRequest, store: str, amounts: dict[str, Decimal]
) -> StoreComparison:
    items = []
    missing = []
    for requested in request.items:
        concept_id = requested.concept_id
        products = catalog.products_for_concept(
            concept_id, request.country, [store], request.diet_tags
        )
        best = _cheapest(_match(product, amounts[concept_id]) for product in products)
        if best is None:
            missing.append(concept_id)
        else:
            items.append(best)
    return StoreComparison(
        store=store,
        items=items,
        total_eur=_total(items),
        promo_savings_eur=_promo_savings(items),
        missing_concepts=missing,
    )


def compare(catalog: ProductCatalog, request: CompareRequest) -> CompareResponse:
    """`request.stores` must be stores of `request.country` (checked by the route)."""
    amounts: dict[str, Decimal] = {}
    for requested in request.items:
        size = catalog.reference_pack_size(requested.concept_id, request.country)
        # None: no store in the country sells it, so it ends up missing everywhere.
        amount = ZERO if size is None else _pack_size(size) * requested.quantity
        amounts[requested.concept_id] = amount

    per_store = [_store_comparison(catalog, request, store, amounts) for store in request.stores]
    rankings = sorted(per_store, key=lambda s: (len(s.missing_concepts), s.total_eur, s.store))

    chosen: dict[str, MatchedStoreItem] = {}
    for requested in request.items:
        concept_id = requested.concept_id
        best = _cheapest(i for s in per_store for i in s.items if i.concept_id == concept_id)
        if best is not None:
            chosen[concept_id] = best
    by_store: defaultdict[str, list[MatchedStoreItem]] = defaultdict(list)
    for item in chosen.values():  # request order
        by_store[item.store].append(item)

    # What each store charges above the split basket for the items it has (never negative:
    # the split takes the cheapest offer of every item).
    overpay = {
        s.store: s.total_eur - _total(chosen[i.concept_id] for i in s.items) for s in per_store
    }
    best_store = rankings[0]
    split_extra = overpay[best_store.store]
    use_split = len(by_store) > 1 and split_extra >= request.min_split_savings_eur
    logger.info(
        "Compare: %d items at %d stores, split saves €%s over %s",
        len(request.items),
        len(request.stores),
        split_extra,
        best_store.store,
    )
    return CompareResponse(
        single_store_rankings=rankings,
        split_basket=SplitBasket(
            stores=[
                SplitStoreGroup(store=store, items=items, total_eur=_total(items))
                for store, items in sorted(by_store.items())
            ],
            total_eur=_total(chosen.values()),
            missing_concepts=[i.concept_id for i in request.items if i.concept_id not in chosen],
            total_savings_vs_worst_eur=max(overpay.values()),
        ),
        recommended_strategy="split_basket" if use_split else "single_store",
        recommended_store=None if use_split or not best_store.items else best_store.store,
        split_extra_savings_eur=split_extra,
        catalog_version=catalog.catalog.version,
        price_date=catalog.catalog.price_date,
    )
