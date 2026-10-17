"""Prices a plan from the catalog and trims it to the budget. Pure and deterministic.

The LLM only says which products and how many packs; every number here comes from the
catalog. Money is `Decimal`, rounded half-up to cents.
"""

from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from app.schemas.catalog import Category, Product
from app.services.catalog import ProductCatalog

CENT = Decimal("0.01")

# Dropped first when over budget; categories not listed come after, as one group.
DROP_PRIORITY: tuple[Category, ...] = ("snacks", "beverages", "frozen", "cleaning", "hygiene")
# Never added by the kcal top-up: not a meal staple, or not food.
TOP_UP_EXCLUDED: frozenset[Category] = frozenset(
    {"beverages", "snacks", "cleaning", "hygiene", "other"}
)


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


def _kcal_per_euro(product: Product) -> float:
    return (product.kcal or 0) / float(product.price_eur)


def top_up_kcal(
    plan: PricedPlan,
    candidates: Iterable[Product],
    budget: Decimal | float,
    target_kcal: float,
    max_packs_per_product: int,
    max_kcal_share: float,
    in_list_min_ratio: float,
    skip_ids: Collection[str] = (),
) -> tuple[PricedPlan, dict[str, int]]:
    """Add single packs until the plan has `target_kcal` or nothing more fits the budget.

    A product qualifies when it is food with energy outside TOP_UP_EXCLUDED and not in
    `skip_ids`, has had fewer than `max_packs_per_product` packs added, its pack fits the
    remaining budget, and with it the product stays at most `max_kcal_share` of
    `target_kcal`. Each step adds one pack of the qualifying product with the most kcal per
    euro, among the plan's products and the other `candidates`; the best product already in
    the plan wins instead if it has at least `in_list_min_ratio` of that kcal per euro.
    Returns the new plan and the packs added per product (empty, with `plan` itself, if
    none).
    """
    budget = round_money(Decimal(str(budget)))
    products = {line.product.id: line.product for line in plan.lines}
    packs = {line.product.id: line.packs for line in plan.lines}
    in_plan = list(products.values())
    others = [p for p in candidates if p.id not in products]
    added: dict[str, int] = {}
    total = plan.total
    kcal = sum((p.kcal or 0) * packs[p.id] for p in in_plan)

    def fits(product: Product) -> bool:
        if product.category in TOP_UP_EXCLUDED or not product.kcal or product.id in skip_ids:
            return False
        if added.get(product.id, 0) >= max_packs_per_product:
            return False
        if product.price_eur > budget - total:
            return False
        return product.kcal * (packs.get(product.id, 0) + 1) <= max_kcal_share * target_kcal

    def best(pool: list[Product]) -> Product | None:
        eligible = [p for p in pool if fits(p)]
        # Most kcal per euro; product id breaks ties so the result is deterministic.
        return min(eligible, key=lambda p: (-_kcal_per_euro(p), p.id), default=None)

    while kcal < target_kcal:
        product = best(in_plan + others)
        if product is None:
            break
        listed = best(in_plan)
        if listed is not None and (
            _kcal_per_euro(listed) >= in_list_min_ratio * _kcal_per_euro(product)
        ):
            product = listed
        if product.id not in products:
            products[product.id] = product
            in_plan.append(product)
            others.remove(product)
        packs[product.id] = packs.get(product.id, 0) + 1
        added[product.id] = added.get(product.id, 0) + 1
        total += product.price_eur
        kcal += product.kcal or 0

    if not added:
        return plan, {}
    return _build((p, packs[p.id]) for p in products.values()), added
