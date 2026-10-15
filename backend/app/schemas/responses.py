"""API response models (the contract mirrored by frontend/src/types.ts).

Every price, total and nutrition value is computed by the server from the catalog.
Money is a number rounded to cents.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.catalog import Category, Country, DietTag, Unit


class Nutrition(BaseModel):
    kcal: float
    protein_g: float
    fat_g: float
    carbs_g: float


class Item(BaseModel):
    product_id: str
    name: str  # in the request language
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
    from_packs: int
    to_packs: int


class Meal(BaseModel):
    name: str
    description: str
    ingredient_ids: list[str]


class DayMenu(BaseModel):
    day: str
    breakfast: Meal
    lunch: Meal
    dinner: Meal
    snack: Meal | None


class GenerateResponse(BaseModel):
    items: list[Item]
    subtotals_by_store: dict[str, float]
    total: float
    budget: float
    budget_remaining: float
    nutrition_totals: Nutrition
    kcal_per_person_day: float = Field(
        description=(
            "nutrition_totals.kcal / (family_size x days). Based on the purchased packs, so "
            "an upper bound of the food available, not what the menu's meals consume."
        )
    )
    trimmed: list[TrimmedItem]
    auto_added: list[str] = Field(
        description=(
            "Meal ingredients the model left out of its list; the server added 1 pack "
            "each (before any trimming)."
        )
    )
    menu: list[DayMenu] | None
    notes: str
    catalog_version: str
    price_date: date
    generated_at: datetime


class CatalogMeta(BaseModel):
    catalog_version: str
    price_date: date
    countries: dict[Country, list[str]]
    diet_tags: list[DietTag]
    categories: list[Category]
