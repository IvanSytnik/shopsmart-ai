"""Menu mode: from per-person portions to packs and eaten kcal. Pure and deterministic.

The LLM gives each meal ingredient as an amount one person eats, in the product's
`portion_unit`: grams, millilitres, pieces, or a fraction of one pack ("pack", e.g. 0.5 of
a frozen pizza). The server adds these up for the household and buys whole packs.
Quantities are `Decimal`, so 0.29 kg is exactly 290 g and 0.25 packs add up exactly.
"""

import math
from collections.abc import Iterable, Mapping
from decimal import ROUND_HALF_UP, Decimal

from app.schemas.catalog import PortionUnit, Product

# Allowed amount_per_person per meal, in the portion unit.
PORTION_BOUNDS: dict[PortionUnit, tuple[Decimal, Decimal]] = {
    "g": (Decimal(5), Decimal(800)),
    "ml": (Decimal(5), Decimal(800)),
    "pcs": (Decimal(1), Decimal(6)),
    "pack": (Decimal("0.25"), Decimal(2)),
}
# Portions are rounded to these steps after scaling.
ROUNDING_STEP: dict[PortionUnit, Decimal] = {
    "g": Decimal(5),
    "ml": Decimal(5),
    "pcs": Decimal(1),
    "pack": Decimal("0.25"),
}

# Menu kcal normalization: a menu below the minimum is scaled up by min/kcal plus a margin,
# at most by MAX_SCALE_UP; one above the maximum is scaled down by max/kcal minus a margin.
SCALE_UP_MARGIN = 1.05
MAX_SCALE_UP = 1.6
SCALE_DOWN_MARGIN = 0.95


def decimal(value: float) -> Decimal:
    return Decimal(str(value))


def pack_quantity(product: Product) -> Decimal:
    """What one pack holds, in the portion unit."""
    if product.portion_unit == "pack":
        return Decimal(1)
    size = decimal(product.pack_size)
    return size * 1000 if product.portion_unit in ("g", "ml") else size


def clamp_portion(product: Product, amount: float) -> float:
    """`amount` moved into the portion unit's PORTION_BOUNDS, to the nearest bound."""
    low, high = PORTION_BOUNDS[product.portion_unit]
    return float(min(max(decimal(amount), low), high))


def round_portion(product: Product, amount: Decimal) -> float:
    """`amount` rounded half up to the portion unit's step (not clamped)."""
    step = ROUNDING_STEP[product.portion_unit]
    return float((amount / step).quantize(Decimal(1), rounding=ROUND_HALF_UP) * step)


def kcal_scale_factor(kcal: float, min_kcal: float, max_kcal: float) -> float | None:
    """How much to scale all portions to bring `kcal` into [min_kcal, max_kcal], or None."""
    if kcal <= 0:
        return None
    if kcal < min_kcal:
        return min(min_kcal / kcal * SCALE_UP_MARGIN, MAX_SCALE_UP)
    if kcal > max_kcal:
        return max_kcal / kcal * SCALE_DOWN_MARGIN
    return None


def scale_portion(product: Product, amount: float, factor: float) -> float:
    """`amount` × `factor`, rounded half up to the unit's step (not yet clamped)."""
    return round_portion(product, decimal(amount) * decimal(factor))


def required_quantities(
    portions: Iterable[tuple[str, float]], family_size: int
) -> dict[str, Decimal]:
    """Total quantity per product, in the portion unit: Σ amount_per_person × family_size.

    Keeps the order in which products first appear.
    """
    totals: dict[str, Decimal] = {}
    for product_id, amount in portions:
        totals[product_id] = totals.get(product_id, Decimal(0)) + decimal(amount) * family_size
    return totals


def packs_needed(product: Product, quantity: Decimal) -> int:
    """Whole packs that cover `quantity` (portion unit); at least one."""
    return max(1, math.ceil(quantity / pack_quantity(product)))


def kcal_per_unit(product: Product) -> float | None:
    """kcal per portion unit (per g, ml, piece or pack); None for non-food."""
    if product.kcal is None:
        return None
    return product.kcal / float(pack_quantity(product))


def eaten_kcal(
    required: Mapping[str, Decimal], packs: Mapping[str, int], products: Mapping[str, Product]
) -> float:
    """kcal the menu's portions provide, limited to what was bought.

    A product trimmed to fewer packs than the menu needs counts only what is bought; a
    removed one (absent from `packs`) counts nothing.
    """
    total = 0.0
    for product_id, quantity in required.items():
        product = products.get(product_id)
        bought = packs.get(product_id, 0)
        density = kcal_per_unit(product) if product is not None else None
        if product is None or density is None or bought == 0:
            continue
        eaten = min(quantity, bought * pack_quantity(product))
        total += float(eaten) * density
    return total
