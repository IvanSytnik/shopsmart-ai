"""Portion arithmetic for menu mode: quantities, pack rounding, eaten kcal."""

from decimal import Decimal

import pytest

from app.schemas.catalog import Product
from app.services.catalog import load_catalog
from app.services.portions import (
    clamp_portion,
    eaten_kcal,
    kcal_scale_factor,
    pack_quantity,
    packs_needed,
    required_quantities,
    scale_portion,
)
from tests.conftest import FIXTURE_CATALOG, MILK

CATALOG = load_catalog(FIXTURE_CATALOG)


def product(product_id: str) -> Product:
    found = CATALOG.get(product_id)
    assert found is not None
    return found


CHICKEN = product("at-lidl-chicken-breast-500g")  # 0.5 kg, 550 kcal
EGGS = product("de-lidl-eggs-10")  # 10 pcs
PIZZA = product("at-penny-frozen-pizza-350g")  # 350 g, portion unit "pack", 840 kcal


def test_pack_quantity_is_in_the_portion_unit() -> None:
    assert pack_quantity(CHICKEN) == 500  # g
    assert pack_quantity(product(MILK)) == 1000  # ml
    assert pack_quantity(EGGS) == 10  # pcs


def test_required_quantity_sums_portions_for_the_household() -> None:
    portions = [(CHICKEN.id, 80)] * 3 + [(MILK, 200)]

    assert required_quantities(portions, family_size=2) == {CHICKEN.id: 480, MILK: 400}


@pytest.mark.parametrize(
    ("quantity", "packs"),
    [(1, 1), (480, 1), (500, 1), (501, 2), (520, 2), (1500, 3)],
)
def test_packs_round_up_to_whole_packs(quantity: int, packs: int) -> None:
    assert packs_needed(CHICKEN, quantity) == packs


def test_pcs_round_up_to_whole_packs() -> None:
    # 2 eggs at breakfast + 1 at dinner, 3 people: 9 eggs -> 1 box of 10; 4 people: 12 -> 2.
    assert packs_needed(EGGS, required_quantities([(EGGS.id, 2), (EGGS.id, 1)], 3)[EGGS.id]) == 1
    assert packs_needed(EGGS, required_quantities([(EGGS.id, 2), (EGGS.id, 1)], 4)[EGGS.id]) == 2


def test_fractional_pack_sizes_are_exact() -> None:
    # 0.29 * 1000 is 289.99999999999997 as a float; 580 g must still be exactly 2 packs.
    odd = CHICKEN.model_copy(update={"pack_size": 0.29})

    assert packs_needed(odd, 580) == 2
    assert packs_needed(odd, 581) == 3


@pytest.mark.parametrize(
    ("unit_product", "amount", "expected"),
    [
        (CHICKEN, 5, 5),
        (CHICKEN, 800, 800),
        (CHICKEN, 3, 5),
        (CHICKEN, 801, 800),
        (EGGS, 1, 1),
        (EGGS, 6, 6),
        (EGGS, 9, 6),
    ],
)
def test_portions_are_clamped_to_the_unit_range(
    unit_product: Product, amount: int, expected: int
) -> None:
    assert clamp_portion(unit_product, amount) == expected


def test_eaten_kcal_counts_portions_not_packs() -> None:
    products = {CHICKEN.id: CHICKEN, MILK: product(MILK)}
    required = {CHICKEN.id: 480, MILK: 400}  # 1.1 kcal/g, 0.64 kcal/ml

    # 1 pack each is bought; only the eaten part counts: 528 + 256.
    assert eaten_kcal(required, {CHICKEN.id: 1, MILK: 1}, products) == pytest.approx(784)


def test_eaten_kcal_is_limited_to_what_was_bought() -> None:
    products = {CHICKEN.id: CHICKEN, MILK: product(MILK)}
    required = {CHICKEN.id: 1200, MILK: 400}

    # Chicken trimmed from 3 packs to 1 (500 g = 550 kcal); milk removed.
    assert eaten_kcal(required, {CHICKEN.id: 1}, products) == pytest.approx(550)


@pytest.mark.parametrize(
    ("kcal", "factor"),
    [
        (1062, 1600 / 1062 * 1.05),
        (500, 1.6),  # capped
        (1600, None),
        (3500, None),
        (8400, 3500 / 8400 * 0.95),
        (0, None),
    ],
)
def test_kcal_scale_factor(kcal: float, factor: float | None) -> None:
    result = kcal_scale_factor(kcal, 1600, 3500)
    if factor is None:
        assert result is None
    else:
        assert result == pytest.approx(factor)


@pytest.mark.parametrize(
    ("unit_product", "amount", "factor", "expected"),
    [
        (CHICKEN, 103, 1.5, 155),  # 154.5 -> nearest 5, half up
        (CHICKEN, 100, 1.58, 160),  # 158 -> 160
        (CHICKEN, 100, 1.56, 155),  # 156 -> 155
        (EGGS, 5, 1.5, 8),  # 7.5 -> 8, half up
        (EGGS, 1, 0.4, 0),  # clamping is a separate step
    ],
)
def test_scaled_portions_are_rounded_to_the_unit_step(
    unit_product: Product, amount: int, factor: float, expected: int
) -> None:
    assert scale_portion(unit_product, amount, factor) == expected


def test_pack_portions_are_fractions_of_one_pack() -> None:
    assert pack_quantity(PIZZA) == 1
    # Half a pizza each for 3 people: 1.5 pizzas -> 2 packs.
    required = required_quantities([(PIZZA.id, 0.5)], family_size=3)
    assert required == {PIZZA.id: Decimal("1.5")}
    assert packs_needed(PIZZA, required[PIZZA.id]) == 2
    assert packs_needed(PIZZA, Decimal("2.00")) == 2  # 0.25 steps add up exactly


def test_pack_portion_kcal_are_per_pack() -> None:
    # Half a pizza eaten out of 1 bought: 420 kcal.
    assert eaten_kcal({PIZZA.id: Decimal("0.5")}, {PIZZA.id: 1}, {PIZZA.id: PIZZA}) == 420


@pytest.mark.parametrize(
    ("amount", "factor", "scaled", "clamped"),
    [(0.5, 1.2, 0.5, 0.5), (0.5, 1.3, 0.75, 0.75), (1.5, 1.6, 2.5, 2.0), (0.25, 0.4, 0.0, 0.25)],
)
def test_pack_portions_round_to_quarters_and_clamp(
    amount: float, factor: float, scaled: float, clamped: float
) -> None:
    assert scale_portion(PIZZA, amount, factor) == scaled
    assert clamp_portion(PIZZA, scaled) == clamped
