import random
from decimal import Decimal
from pathlib import Path

import pytest

from app.services.catalog import ProductCatalog, load_catalog
from app.services.pricing import (
    BudgetChange,
    InvalidPacksError,
    Nutrition,
    PlanLine,
    PricedPlan,
    ProductNotAllowedError,
    UnknownProductError,
    enforce_budget,
    price_plan,
    round_money,
)

FIXTURE = Path(__file__).parent / "fixtures" / "catalog_small.json"

# AT products from the fixture, by short name.
MILK = "at-lidl-milk-1l"  # 1.29, dairy
OAT = "at-lidl-oat-drink-1l"  # 1.49, beverages
CHICKEN = "at-lidl-chicken-breast-500g"  # 5.99, meat
APPLES = "at-lidl-apples-1kg"  # 1.99, fruits
CHIPS = "at-lidl-potato-chips-175g"  # 1.79, snacks
SOAP = "at-lidl-dish-soap-500ml"  # 0.99, cleaning
GOUDA = "at-penny-cheese-gouda-400g"  # 4.49, dairy
PASTA = "at-penny-pasta-500g"  # 0.99, pantry
PIZZA = "at-penny-frozen-pizza-350g"  # 2.79, frozen
TOOTHPASTE = "at-penny-toothpaste-75ml"  # 1.49, hygiene


@pytest.fixture(scope="module")
def catalog() -> ProductCatalog:
    return load_catalog(FIXTURE)


@pytest.fixture(scope="module")
def at_ids(catalog: ProductCatalog) -> set[str]:
    return {p.id for p in catalog.candidates("AT", ["Lidl", "Penny"], [])}


def plan(catalog: ProductCatalog, allowed: set[str], **packs: int) -> PricedPlan:
    """Build a plan from SHORT_NAME=packs keyword arguments."""
    return price_plan([PlanLine(globals()[k], n) for k, n in packs.items()], catalog, allowed)


def packs_of(priced: PricedPlan) -> dict[str, int]:
    return {line.product.id: line.packs for line in priced.lines}


# --- price_plan ----------------------------------------------------------------


def test_price_plan_totals_subtotals_and_nutrition(
    catalog: ProductCatalog, at_ids: set[str]
) -> None:
    priced = plan(catalog, at_ids, MILK=2, CHICKEN=1, SOAP=3, GOUDA=1)

    assert [line.line_total for line in priced.lines] == [
        Decimal("2.58"),
        Decimal("5.99"),
        Decimal("2.97"),
        Decimal("4.49"),
    ]
    assert priced.store_subtotals == {"Lidl": Decimal("11.54"), "Penny": Decimal("4.49")}
    assert priced.total == Decimal("16.03")
    # milk x2 + chicken + gouda; soap is non-food and adds nothing.
    assert priced.nutrition == Nutrition(kcal=3250, protein_g=283, fat_g=190, carbs_g=96)
    soap = priced.lines[2]
    assert soap.nutrition is None


def test_price_plan_money_is_exact_decimal(catalog: ProductCatalog, at_ids: set[str]) -> None:
    # As floats, 0.99 * 3 == 2.9699999999999998.
    priced = plan(catalog, at_ids, PASTA=3)

    assert str(priced.total) == "2.97"
    assert str(priced.lines[0].line_total) == "2.97"


def test_price_plan_total_always_has_cents(catalog: ProductCatalog, at_ids: set[str]) -> None:
    priced = plan(catalog, at_ids, PASTA=1, SOAP=1)  # 0.99 + 0.99

    assert str(priced.total) == "1.98"
    assert str(plan(catalog, at_ids).total) == "0.00"


@pytest.mark.parametrize(
    ("amount", "expected"),
    [("0.125", "0.13"), ("0.135", "0.14"), ("2.675", "2.68"), ("2.674", "2.67"), ("5", "5.00")],
)
def test_round_money_is_half_up(amount: str, expected: str) -> None:
    assert str(round_money(Decimal(amount))) == expected


def test_price_plan_merges_repeated_ids(catalog: ProductCatalog, at_ids: set[str]) -> None:
    lines = [PlanLine(MILK, 1), PlanLine(APPLES, 1), PlanLine(MILK, 2)]

    priced = price_plan(lines, catalog, at_ids)

    assert packs_of(priced) == {MILK: 3, APPLES: 1}
    assert [line.product.id for line in priced.lines] == [MILK, APPLES]


def test_price_plan_rejects_unknown_product(catalog: ProductCatalog, at_ids: set[str]) -> None:
    with pytest.raises(UnknownProductError, match="no-such-product"):
        price_plan([PlanLine(MILK, 1), PlanLine("no-such-product", 1)], catalog, at_ids)


def test_price_plan_rejects_product_outside_candidates(
    catalog: ProductCatalog, at_ids: set[str]
) -> None:
    # Exists in the catalog, but in Germany.
    with pytest.raises(ProductNotAllowedError, match="de-lidl-milk-1l"):
        price_plan([PlanLine("de-lidl-milk-1l", 1)], catalog, at_ids)


def test_price_plan_rejects_product_excluded_by_diet(catalog: ProductCatalog) -> None:
    vegan = {p.id for p in catalog.candidates("AT", ["Lidl", "Penny"], ["vegan"])}

    with pytest.raises(ProductNotAllowedError, match=CHICKEN):
        price_plan([PlanLine(CHICKEN, 1)], catalog, vegan)


@pytest.mark.parametrize("packs", [0, -1])
def test_price_plan_rejects_non_positive_packs(
    catalog: ProductCatalog, at_ids: set[str], packs: int
) -> None:
    with pytest.raises(InvalidPacksError):
        price_plan([PlanLine(MILK, packs)], catalog, at_ids)


# --- enforce_budget --------------------------------------------------------------


@pytest.mark.parametrize("budget", [Decimal("16.03"), Decimal("100"), 16.03])
def test_plan_within_budget_is_untouched(
    catalog: ProductCatalog, at_ids: set[str], budget: Decimal | float
) -> None:
    priced = plan(catalog, at_ids, MILK=2, CHICKEN=1, SOAP=3, GOUDA=1)  # 16.03

    result, changes = enforce_budget(priced, budget, protected_ids=set())

    assert result is priced
    assert changes == []


def test_packs_are_reduced_before_anything_is_dropped(
    catalog: ProductCatalog, at_ids: set[str]
) -> None:
    priced = plan(catalog, at_ids, CHICKEN=3, APPLES=2, CHIPS=1)  # 17.97 + 3.98 + 1.79 = 23.74

    result, changes = enforce_budget(priced, Decimal("20"), protected_ids=set())

    # One chicken pack (the most expensive line) is enough; the snack stays.
    assert packs_of(result) == {CHICKEN: 2, APPLES: 2, CHIPS: 1}
    assert result.total == Decimal("17.75")
    assert changes == [BudgetChange(CHICKEN, "reduced", 3, 2)]


def test_most_expensive_line_is_re_evaluated_after_each_reduction(
    catalog: ProductCatalog, at_ids: set[str]
) -> None:
    # Gouda x2 (8.98) is the priciest line; after one pack (4.49) milk x4 (5.16) is.
    priced = plan(catalog, at_ids, GOUDA=2, MILK=4)  # 8.98 + 5.16 = 14.14

    result, changes = enforce_budget(priced, Decimal("8.40"), protected_ids=set())

    assert packs_of(result) == {GOUDA: 1, MILK: 3}
    assert result.total == Decimal("8.36")
    assert changes == [
        BudgetChange(GOUDA, "reduced", 2, 1),
        BudgetChange(MILK, "reduced", 4, 3),
    ]


# One pack each, 16.53 in total. Drop order: snacks, beverages, frozen, cleaning, hygiene,
# then everything else most expensive first (chicken 5.99 before apples 1.99).
ONE_EACH = {
    "CHICKEN": 1,
    "CHIPS": 1,
    "OAT": 1,
    "PIZZA": 1,
    "SOAP": 1,
    "TOOTHPASTE": 1,
    "APPLES": 1,
}


@pytest.mark.parametrize(
    ("budget", "removed"),
    [
        ("16.00", [CHIPS]),
        ("14.00", [CHIPS, OAT]),
        ("12.00", [CHIPS, OAT, PIZZA]),
        ("10.00", [CHIPS, OAT, PIZZA, SOAP]),
        ("9.00", [CHIPS, OAT, PIZZA, SOAP, TOOTHPASTE]),
        ("7.00", [CHIPS, OAT, PIZZA, SOAP, TOOTHPASTE, CHICKEN]),
        ("1.00", [CHIPS, OAT, PIZZA, SOAP, TOOTHPASTE, CHICKEN, APPLES]),
    ],
)
def test_lines_are_dropped_by_category_priority(
    catalog: ProductCatalog, at_ids: set[str], budget: str, removed: list[str]
) -> None:
    priced = plan(catalog, at_ids, **ONE_EACH)

    result, changes = enforce_budget(priced, Decimal(budget), protected_ids=set())

    assert set(packs_of(result)) == set(packs_of(priced)) - set(removed)
    assert {c.product_id for c in changes} == set(removed)
    assert all(c.action == "removed" and c.packs_after == 0 for c in changes)
    assert result.total <= Decimal(budget)


def test_drop_within_a_category_is_most_expensive_first(
    catalog: ProductCatalog, at_ids: set[str]
) -> None:
    priced = plan(catalog, at_ids, MILK=1, GOUDA=1)  # both dairy: 1.29, 4.49

    result, _ = enforce_budget(priced, Decimal("2"), protected_ids=set())

    assert packs_of(result) == {MILK: 1}


def test_protected_lines_are_trimmed_last(catalog: ProductCatalog, at_ids: set[str]) -> None:
    priced = plan(catalog, at_ids, CHICKEN=2, APPLES=1, CHIPS=1)  # 11.98 + 1.99 + 1.79

    # Every unprotected line goes, even the "others" one, before the protected chicken...
    result, changes = enforce_budget(priced, Decimal("12"), protected_ids={CHICKEN})
    assert packs_of(result) == {CHICKEN: 2}
    assert {c.product_id for c in changes} == {APPLES, CHIPS}

    # ...which then loses packs like any other line.
    result, changes = enforce_budget(priced, Decimal("6"), protected_ids={CHICKEN})
    assert packs_of(result) == {CHICKEN: 1}
    assert BudgetChange(CHICKEN, "reduced", 2, 1) in changes


def test_protected_lines_use_the_same_order(catalog: ProductCatalog, at_ids: set[str]) -> None:
    priced = plan(catalog, at_ids, **ONE_EACH)

    result, _ = enforce_budget(priced, Decimal("8"), protected_ids={CHICKEN, CHIPS, APPLES})

    # Unprotected all gone (9.77 left), then the protected snack goes before the pricier
    # protected chicken (7.98 left).
    assert packs_of(result) == {CHICKEN: 1, APPLES: 1}


def test_changes_are_reported_in_plan_order(catalog: ProductCatalog, at_ids: set[str]) -> None:
    priced = plan(catalog, at_ids, APPLES=1, CHIPS=1, OAT=1)

    _, changes = enforce_budget(priced, Decimal("2"), protected_ids=set())

    assert [c.product_id for c in changes] == [CHIPS, OAT]


def test_trimmed_plan_is_repriced(catalog: ProductCatalog, at_ids: set[str]) -> None:
    priced = plan(catalog, at_ids, MILK=3, CHICKEN=1, CHIPS=1)

    result, _ = enforce_budget(priced, Decimal("8"), protected_ids=set())

    assert result == price_plan(
        [PlanLine(line.product.id, line.packs) for line in result.lines], catalog, at_ids
    )


def test_random_plans_never_exceed_budget(catalog: ProductCatalog) -> None:
    rng = random.Random(20261014)
    trimmed = protected_touched = 0
    for iteration in range(200):
        country = rng.choice(["AT", "DE"])
        candidates = catalog.candidates(country, ["Lidl", "Penny"], [])
        allowed = {p.id for p in candidates}
        chosen = rng.sample(candidates, rng.randint(1, len(candidates)))
        lines = [PlanLine(p.id, rng.randint(1, 5)) for p in chosen]
        protected = {p.id for p in chosen if rng.random() < 0.3}
        budget = Decimal(rng.randint(0, 8000)) / 100
        priced = price_plan(lines, catalog, allowed)

        result, changes = enforce_budget(priced, budget, protected)

        context = f"iteration {iteration}, budget {budget}"
        assert result.total <= budget, context
        assert result.total == sum((line.line_total for line in result.lines), Decimal(0))
        before, after = packs_of(priced), packs_of(result)
        assert all(1 <= n <= before[i] for i, n in after.items()), context
        if priced.total <= budget:
            assert (result, changes) == (priced, []), context
        assert {c.product_id for c in changes} == {i for i in before if after.get(i) != before[i]}
        # Protected lines are only touched once every unprotected line is gone.
        if any(c.product_id in protected for c in changes):
            assert set(after) <= protected, context
            protected_touched += 1
        trimmed += bool(changes)
    # The seed must keep exercising both trimming and the protected fallback.
    assert trimmed >= 50 and protected_touched >= 10
