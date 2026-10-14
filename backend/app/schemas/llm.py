"""Shape of the plan the LLM must return (Structured Outputs, strict mode).

Built per request: product ids are an enum of that request's candidates, so the model can
only pick products the server knows. The model never sends prices, totals or nutrition;
those are computed from the catalog.

Strict mode needs every field to be required: optional values are `X | None` and the
model sends `null`.
"""

from collections.abc import Sequence
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, create_model

# Above this, product ids are plain strings checked by the server: OpenAI allows at most
# 1000 enum values per schema, and the ids appear twice (lines and meal ingredients).
MAX_ENUM_IDS = 500
MAX_PACKS = 20


# Typing view of the generated models, for code that reads a parsed plan.
class LLMLine(Protocol):
    product_id: str
    packs: int


class LLMMeal(Protocol):
    name: str
    description: str
    ingredient_ids: list[str]


class LLMDayMenu(Protocol):
    day: str
    breakfast: LLMMeal
    lunch: LLMMeal
    dinner: LLMMeal
    snack: LLMMeal | None


class LLMPlan(Protocol):
    lines: list[LLMLine]
    menu: list[LLMDayMenu] | None
    notes: str


def build_plan_model(candidate_ids: Sequence[str]) -> type[BaseModel]:
    """The response model for one request, restricted to `candidate_ids`."""
    if not candidate_ids:
        raise ValueError("candidate_ids must not be empty")
    product_id: Any = Literal[tuple(candidate_ids)] if len(candidate_ids) <= MAX_ENUM_IDS else str

    line = create_model(
        "LLMLine",
        product_id=(product_id, ...),
        packs=(int, Field(ge=1, le=MAX_PACKS)),
    )
    meal = create_model(
        "LLMMeal",
        name=(str, ...),
        description=(str, ...),
        ingredient_ids=(list[product_id], ...),
    )
    day_menu = create_model(
        "LLMDayMenu",
        day=(str, ...),
        breakfast=(meal, ...),
        lunch=(meal, ...),
        dinner=(meal, ...),
        snack=(meal | None, ...),
    )
    return create_model(
        "LLMPlan",
        lines=(list[line], ...),
        menu=(list[day_menu] | None, ...),
        notes=(str, ...),
    )
