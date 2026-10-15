"""Portion arithmetic for menu mode: quantities, pack rounding, eaten kcal."""

import pytest

from app.schemas.catalog import Product
from app.services.catalog import load_catalog
from app.services.portions import (
    eaten_kcal,
    pack_quantity,
    packs_needed,
    portion_in_bounds,
    required_quantities,
)
from tests.conftest import FIXTURE_CATALOG, MILK

CATALOG = load_catalog(FIXTURE_CATALOG)


def product(product_id: str) -> Product:
    found = CATALOG.get(product_id)
    assert found is not None
    return found


CHICKEN = product("at-lidl-chicken-breast-500g")  # 0.5 kg, 550 kcal
EGGS = product("de-lidl-eggs-10")  # 10 pcs


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
    ("unit_product", "amount", "ok"),
    [
        (CHICKEN, 5, True),
        (CHICKEN, 800, True),
        (CHICKEN, 4, False),
        (CHICKEN, 801, False),
        (EGGS, 1, True),
        (EGGS, 6, True),
        (EGGS, 7, False),
    ],
)
def test_portion_bounds_depend_on_the_unit(unit_product: Product, amount: int, ok: bool) -> None:
    assert portion_in_bounds(unit_product, amount) is ok


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
