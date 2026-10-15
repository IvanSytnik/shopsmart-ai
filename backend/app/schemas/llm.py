"""Shape of the plan the LLM must return (Structured Outputs, strict mode).

Built per request: product ids are an enum of that request's candidates, so the model can
only pick products the server knows. The model never sends prices, totals or nutrition;
those are computed from the catalog.

Strict mode needs every field to be required: optional values are `X | None` and the
model sends `null`.
"""

from collections.abc import Sequence
from typing import Any, Literal, Protocol

from openai.lib._pydantic import to_strict_json_schema
from pydantic import BaseModel, Field, create_model

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
    menu: list[LLMDayMenu] | None
    lines: list[LLMLine]
    notes: str


def count_enum_values(schema: dict[str, Any]) -> int:
    """Total enum values in a JSON schema, counting a `$ref` once per place it is used.

    Pydantic puts the id enum in `$defs` and references it from lines and from each of the
    four meals, so one candidate list appears about five times once refs are expanded.
    """
    defs = schema.get("$defs", {})

    def walk(node: object, seen: frozenset[str]) -> int:
        if isinstance(node, list):
            return sum(walk(item, seen) for item in node)
        if not isinstance(node, dict):
            return 0
        total = len(node["enum"]) if isinstance(node.get("enum"), list) else 0
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/") and ref not in seen:
            total += walk(defs.get(ref.removeprefix("#/$defs/")), seen | {ref})
        return total + sum(walk(v, seen) for k, v in node.items() if k not in ("enum", "$defs"))

    return walk(schema, frozenset())


def build_plan_model(candidate_ids: Sequence[str], max_enum_values: int) -> type[BaseModel]:
    """The response model for one request, restricted to `candidate_ids`.

    OpenAI strict mode limits the total number of enum values in one schema (1000 at the
    time of writing; whether `$ref`s are expanded isn't documented). So ids are a `Literal`
    only while the schema the SDK sends, counted with refs expanded, stays within
    `max_enum_values` (a conservative setting). Otherwise they are plain strings and the
    planner rejects unknown ids itself.
    """
    if not candidate_ids:
        raise ValueError("candidate_ids must not be empty")
    model = _plan_model(Literal[tuple(candidate_ids)])
    if count_enum_values(to_strict_json_schema(model)) <= max_enum_values:
        return model
    return _plan_model(str)


def _plan_model(product_id: Any) -> type[BaseModel]:
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
    # Field order is generation order: the model writes the menu first, then the lines
    # that buy it.
    return create_model(
        "LLMPlan",
        menu=(list[day_menu] | None, ...),
        lines=(list[line], ...),
        notes=(str, ...),
    )
