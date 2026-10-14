"""API response models (the contract mirrored by frontend/src/types.ts)."""

from pydantic import BaseModel


class Meal(BaseModel):
    name: str
    description: str
    calories: int | None = None


class DayMenu(BaseModel):
    day: str
    breakfast: Meal
    lunch: Meal
    dinner: Meal
    snack: Meal | None = None


class ShoppingItem(BaseModel):
    product: str
    quantity: str
    store: str
    approx_price: float
    category: str
    calories: int | None = 0
    protein: float | None = 0
    fat: float | None = 0
    carbs: float | None = 0


class GenerateResponse(BaseModel):
    items: list[ShoppingItem]
    total_cost: float
    notes: str
    generated_at: str
    menu: list[DayMenu] | None = None
