"""Menu mode: from per-person portions to packs and eaten kcal. Pure and deterministic.

The LLM gives each meal ingredient as an amount one person eats, in the product's portion
unit: grams for products sold by kg, millilitres for l, pieces for pcs and pack. The server
adds these up for the household and buys whole packs.
"""

import math
from collections.abc import Iterable, Mapping
from decimal import Decimal

from app.schemas.catalog import Product, Unit

PORTION_UNIT: dict[Unit, str] = {"kg": "g", "l": "ml", "pcs": "pcs", "pack": "pcs"}
# Allowed amount_per_person per meal, in the portion unit.
PORTION_BOUNDS: dict[Unit, tuple[int, int]] = {
    "kg": (5, 800),
    "l": (5, 800),
    "pcs": (1, 6),
    "pack": (1, 6),
}


def pack_quantity(product: Product) -> Decimal:
    """What one pack holds, in the portion unit. Decimal, so 0.29 kg is exactly 290 g."""
    size = Decimal(str(product.pack_size))
    return size * 1000 if product.unit in ("kg", "l") else size


def clamp_portion(product: Product, amount: int) -> int:
    """`amount` moved into the product unit's PORTION_BOUNDS, to the nearest bound."""
    low, high = PORTION_BOUNDS[product.unit]
    return min(max(amount, low), high)


# Menu kcal normalization: a menu below the minimum is scaled up by min/kcal plus a margin,
# at most by MAX_SCALE_UP; one above the maximum is scaled down by max/kcal minus a margin.
SCALE_UP_MARGIN = 1.05
MAX_SCALE_UP = 1.6
SCALE_DOWN_MARGIN = 0.95
# Scaled portions are rounded to these steps (portion unit).
ROUNDING_STEP: dict[Unit, int] = {"kg": 5, "l": 5, "pcs": 1, "pack": 1}


def kcal_scale_factor(kcal: float, min_kcal: float, max_kcal: float) -> float | None:
    """How much to scale all portions to bring `kcal` into [min_kcal, max_kcal], or None."""
    if kcal <= 0:
        return None
    if kcal < min_kcal:
        return min(min_kcal / kcal * SCALE_UP_MARGIN, MAX_SCALE_UP)
    if kcal > max_kcal:
        return max_kcal / kcal * SCALE_DOWN_MARGIN
    return None


def scale_portion(product: Product, amount: int, factor: float) -> int:
    """`amount` × `factor`, rounded half up to the unit's step (not yet clamped)."""
    step = ROUNDING_STEP[product.unit]
    return math.floor(amount * factor / step + 0.5) * step


def required_quantities(portions: Iterable[tuple[str, int]], family_size: int) -> dict[str, int]:
    """Total quantity per product, in the portion unit: Σ amount_per_person × family_size.

    Keeps the order in which products first appear.
    """
    totals: dict[str, int] = {}
    for product_id, amount in portions:
        totals[product_id] = totals.get(product_id, 0) + amount * family_size
    return totals


def packs_needed(product: Product, quantity: int) -> int:
    """Whole packs that cover `quantity` (portion unit); at least one."""
    return max(1, math.ceil(Decimal(quantity) / pack_quantity(product)))


def kcal_per_unit(product: Product) -> float | None:
    """kcal per portion unit (per g, ml or piece); None for non-food."""
    if product.kcal is None:
        return None
    return product.kcal / float(pack_quantity(product))


def eaten_kcal(
    required: Mapping[str, int], packs: Mapping[str, int], products: Mapping[str, Product]
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
        eaten = min(Decimal(quantity), bought * pack_quantity(product))
        total += float(eaten) * density
    return total
