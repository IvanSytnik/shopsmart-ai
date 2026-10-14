"""Prices a plan from the catalog and trims it to the budget. Pure and deterministic.

The LLM only says which products and how many packs; every number here comes from the
catalog. Money is `Decimal`, rounded half-up to cents.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from app.schemas.catalog import Category, Product
from app.services.catalog import ProductCatalog

CENT = Decimal("0.01")

# Dropped first when over budget; categories not listed come after, as one group.
DROP_PRIORITY: tuple[Category, ...] = ("snacks", "beverages", "frozen", "cleaning", "hygiene")


class PricingError(Exception):
    """A plan line that can't be priced; the message names the product id."""


class UnknownProductError(PricingError):
    pass


class ProductNotAllowedError(PricingError):
    """The product exists but isn't among the candidates for this request."""


class InvalidPacksError(PricingError):
    pass


class BudgetUnreachableError(PricingError):
    pass


def round_money(amount: Decimal) -> Decimal:
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PlanLine:
    product_id: str
    packs: int


@dataclass(frozen=True)
class Nutrition:
    kcal: float = 0
    protein_g: float = 0
    fat_g: float = 0
    carbs_g: float = 0


@dataclass(frozen=True)
class PricedLine:
    product: Product
    packs: int
    line_total: Decimal
    nutrition: Nutrition | None  # None for non-food


@dataclass(frozen=True)
class PricedPlan:
    lines: tuple[PricedLine, ...]
    store_subtotals: dict[str, Decimal]
    total: Decimal
    nutrition: Nutrition


@dataclass(frozen=True)
class BudgetChange:
    product_id: str
    action: Literal["reduced", "removed"]
    packs_before: int
    packs_after: int


def _price_line(product: Product, packs: int) -> PricedLine:
    nutrition = None
    if product.kcal is not None:
        nutrition = Nutrition(
            kcal=product.kcal * packs,
            protein_g=(product.protein_g or 0) * packs,
            fat_g=(product.fat_g or 0) * packs,
            carbs_g=(product.carbs_g or 0) * packs,
        )
    return PricedLine(product, packs, round_money(product.price_eur * packs), nutrition)


def _build(items: Iterable[tuple[Product, int]]) -> PricedPlan:
    lines = tuple(_price_line(product, packs) for product, packs in items)
    subtotals: dict[str, Decimal] = {}
    for line in lines:
        store = line.product.store
        subtotals[store] = subtotals.get(store, Decimal("0")) + line.line_total
    foods = [line.nutrition for line in lines if line.nutrition is not None]
    nutrition = Nutrition(
        kcal=round(sum(n.kcal for n in foods), 1),
        protein_g=round(sum(n.protein_g for n in foods), 1),
        fat_g=round(sum(n.fat_g for n in foods), 1),
        carbs_g=round(sum(n.carbs_g for n in foods), 1),
    )
    total = round_money(sum((line.line_total for line in lines), Decimal("0")))
    return PricedPlan(lines, subtotals, total, nutrition)


def price_plan(
    lines: Sequence[PlanLine], catalog: ProductCatalog, allowed_ids: set[str]
) -> PricedPlan:
    """Price `lines` from the catalog. Repeated product ids are merged, first one's position.

    Raises `UnknownProductError`, `ProductNotAllowedError` (not in `allowed_ids`) or
    `InvalidPacksError` (packs < 1).
    """
    products: dict[str, Product] = {}
    packs_by_id: dict[str, int] = {}
    for line in lines:
        product = catalog.get(line.product_id)
        if product is None:
            raise UnknownProductError(f"unknown product id: {line.product_id!r}")
        if line.product_id not in allowed_ids:
            raise ProductNotAllowedError(f"product not allowed here: {line.product_id!r}")
        if line.packs < 1:
            raise InvalidPacksError(f"packs must be >= 1 for {line.product_id!r}")
        products[product.id] = product
        packs_by_id[product.id] = packs_by_id.get(product.id, 0) + line.packs
    return _build((products[i], n) for i, n in packs_by_id.items())


def _drop_rank(product: Product) -> int:
    if product.category in DROP_PRIORITY:
        return DROP_PRIORITY.index(product.category)
    return len(DROP_PRIORITY)


def _next_trim(packs: dict[str, int], products: dict[str, Product], ids: set[str]) -> str | None:
    """Pick the line in `ids` to trim next: reduce before drop, see `enforce_budget`."""

    def line_total(product_id: str) -> Decimal:
        return products[product_id].price_eur * packs[product_id]

    reducible = [i for i in ids if packs[i] > 1]
    if reducible:
        # Most expensive line first; product id breaks ties so the result is deterministic.
        return min(reducible, key=lambda i: (-line_total(i), i))
    if ids:
        return min(ids, key=lambda i: (_drop_rank(products[i]), -line_total(i), i))
    return None


def enforce_budget(
    plan: PricedPlan, budget: Decimal | float, protected_ids: set[str]
) -> tuple[PricedPlan, list[BudgetChange]]:
    """Trim `plan` until its total is <= `budget`; return the new plan and what changed.

    Until the plan fits, one step at a time:
    1. unprotected lines with more than one pack lose a pack, most expensive line first;
    2. otherwise an unprotected line is removed: by category (`DROP_PRIORITY`, then the
       rest), most expensive first within a category;
    3. protected lines last, in the same order.

    Changes are reported once per product: original packs -> final packs (0 = removed).
    """
    budget = round_money(Decimal(str(budget)))
    if budget < 0:
        raise BudgetUnreachableError(f"budget must not be negative: {budget}")
    if plan.total <= budget:
        return plan, []

    products = {line.product.id: line.product for line in plan.lines}
    original = {line.product.id: line.packs for line in plan.lines}
    packs = dict(original)
    order = list(original)  # keep the plan's line order in the result

    def total() -> Decimal:
        return sum((products[i].price_eur * n for i, n in packs.items()), Decimal("0"))

    while round_money(total()) > budget:
        unprotected = {i for i in packs if i not in protected_ids}
        product_id = _next_trim(packs, products, unprotected) or _next_trim(
            packs, products, set(packs)
        )
        if product_id is None:  # nothing left, and an empty plan costs 0 <= budget
            raise BudgetUnreachableError(f"cannot fit plan into budget {budget}")
        if packs[product_id] > 1:
            packs[product_id] -= 1
        else:
            del packs[product_id]

    trimmed = _build((products[i], packs[i]) for i in order if i in packs)
    changes = [
        BudgetChange(
            product_id=i,
            action="reduced" if packs.get(i, 0) else "removed",
            packs_before=original[i],
            packs_after=packs.get(i, 0),
        )
        for i in order
        if packs.get(i, 0) != original[i]
    ]
    if trimmed.total > budget:  # can't happen: the loop stops at <= budget
        raise BudgetUnreachableError(f"trimmed total {trimmed.total} exceeds budget {budget}")
    return trimmed, changes
