"""API response models (the contract mirrored by frontend/src/types.ts).

Every price, total and nutrition value is computed by the server from the catalog.
Money is a number rounded to cents.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.catalog import Category, Country, DietTag, LocalizedName, Unit


class Nutrition(BaseModel):
    kcal: float
    protein_g: float
    fat_g: float
    carbs_g: float


class Item(BaseModel):
    product_id: str
    name: str  # in the request language
    names: LocalizedName  # all languages, so a client can switch language without a new plan
    store: str
    category: Category
    packs: int
    pack_size: float
    unit: Unit
    unit_price: float  # per pack
    line_total: float
    nutrition: Nutrition | None  # for all packs; None for non-food


class TrimmedItem(BaseModel):
    """A line the server cut to fit the budget; `to_packs` 0 means removed."""

    product_id: str
    name: str  # in the request language; removed lines aren't in `items`
    names: LocalizedName
    from_packs: int
    to_packs: int


class MealIngredient(BaseModel):
    product_id: str
    # One person's amount in this meal: grams (unit kg), ml (unit l) or pieces (pcs, pack).
    amount_per_person: int


class Meal(BaseModel):
    name: str
    description: str
    ingredients: list[MealIngredient]


class DayMenu(BaseModel):
    day: str
    breakfast: Meal
    lunch: Meal
    dinner: Meal
    snack: Meal | None


# low_kcal: a menu whose eaten kcal are still below Settings.min_kcal_per_person_day
# after the final attempt (and any trimming).
# budget_trimmed: the server cut lines to fit the budget (see `trimmed`).
Warning = Literal["low_kcal", "budget_trimmed"]
KcalBasis = Literal["menu", "purchased"]


class GenerateResponse(BaseModel):
    items: list[Item]
    subtotals_by_store: dict[str, float]
    total: float
    budget: float
    budget_remaining: float
    nutrition_totals: Nutrition
    kcal_per_person_day: float = Field(
        description=(
            "kcal / (family_size x days), see `kcal_basis`. Menu mode: what the menu's "
            "portions provide (limited to what was bought after trimming). Shopping mode: "
            "nutrition_totals.kcal of the purchased packs, an upper bound."
        )
    )
    kcal_basis: KcalBasis
    trimmed: list[TrimmedItem]
    menu: list[DayMenu] | None
    notes: str
    warnings: list[Warning]
    catalog_version: str
    price_date: date
    generated_at: datetime


class CatalogMeta(BaseModel):
    catalog_version: str
    price_date: date
    countries: dict[Country, list[str]]
    diet_tags: list[DietTag]
    categories: list[Category]
