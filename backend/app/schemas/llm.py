"""Shape of the JSON the LLM is asked to return.

Kept separate from the API response models: the LLM output is untrusted input that gets
validated and mapped, not passed through.
"""

from pydantic import BaseModel, Field


class LLMMeal(BaseModel):
    name: str
    description: str
    calories: int | None = None


class LLMDayMenu(BaseModel):
    day: str
    breakfast: LLMMeal
    lunch: LLMMeal
    dinner: LLMMeal
    snack: LLMMeal | None = None


class LLMShoppingItem(BaseModel):
    product: str
    quantity: str
    store: str
    approx_price: float
    category: str
    calories: int | None = 0
    protein: float | None = 0
    fat: float | None = 0
    carbs: float | None = 0


class LLMPlan(BaseModel):
    items: list[LLMShoppingItem] = Field(default_factory=list)
    total_cost: float = 0
    notes: str = ""
    menu: list[LLMDayMenu] | None = None
