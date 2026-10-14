"""Shape of the plan the LLM must return (Structured Outputs, strict mode).

Strict mode needs every field to be required: no defaults; optional values are
`X | None` and the model sends `null`. Kept separate from the API response models:
the LLM output is untrusted input that gets validated and mapped, not passed through.
"""

from pydantic import BaseModel


class LLMMeal(BaseModel):
    name: str
    description: str
    calories: int | None


class LLMDayMenu(BaseModel):
    day: str
    breakfast: LLMMeal
    lunch: LLMMeal
    dinner: LLMMeal
    snack: LLMMeal | None


class LLMShoppingItem(BaseModel):
    product: str
    quantity: str
    store: str
    approx_price: float
    category: str
    calories: int | None
    protein: float | None
    fat: float | None
    carbs: float | None


class LLMPlan(BaseModel):
    items: list[LLMShoppingItem]
    total_cost: float
    notes: str
    menu: list[LLMDayMenu] | None
