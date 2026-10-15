"""Shape of the plan the LLM must return (Structured Outputs, strict mode).

Built per request: product ids are an enum of that request's candidates, so the model can
only pick products the server knows. The model never sends prices, totals or nutrition;
those are computed from the catalog.

Shopping mode: the model picks products and pack counts (`lines`).
Menu mode: the model picks dishes and per-person portions; the server derives packs.

Strict mode needs every field to be required: optional values are `X | None` and the
model sends `null`.
"""

from collections.abc import Sequence
from typing import Any, Literal, Protocol

from openai.lib._pydantic import to_strict_json_schema
from pydantic import BaseModel, Field, create_model

from app.schemas.requests import Mode

MAX_PACKS = 20
# Schema-level bounds for amount_per_person; the per-unit limits (g/ml 5-800, pcs 1-6,
# pack 0.25-2) are applied by the server, see app.services.portions.PORTION_BOUNDS.
MIN_PORTION = 0.25
MAX_PORTION = 800


# Typing view of the generated models, for code that reads a parsed plan.
class LLMLine(Protocol):
    product_id: str
    packs: int


class LLMShoppingPlan(Protocol):
    lines: list[LLMLine]
    notes: str


class LLMIngredient(Protocol):
    product_id: str
    amount_per_person: float


class LLMMeal(Protocol):
    name: str
    description: str
    ingredients: list[LLMIngredient]


class LLMDayMenu(Protocol):
    day: str
    breakfast: LLMMeal
    lunch: LLMMeal
    dinner: LLMMeal
    snack: LLMMeal | None


class LLMMenuPlan(Protocol):
    menu: list[LLMDayMenu]
    notes: str


def count_enum_values(schema: dict[str, Any]) -> int:
    """Total enum values in a JSON schema, counting a `$ref` once per place it is used.

    Pydantic puts the id enum in `$defs` and references it from every place that uses it
    (in menu mode, each of the four meals), so one candidate list can appear several times
    once refs are expanded.
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


def build_plan_model(
    candidate_ids: Sequence[str], max_enum_values: int, mode: Mode
) -> type[BaseModel]:
    """The response model for one request, restricted to `candidate_ids`.

    OpenAI strict mode limits the total number of enum values in one schema (1000 at the
    time of writing; whether `$ref`s are expanded isn't documented). So ids are a `Literal`
    only while the schema the SDK sends, counted with refs expanded, stays within
    `max_enum_values` (a conservative setting). Otherwise they are plain strings and the
    planner rejects unknown ids itself.
    """
    if not candidate_ids:
        raise ValueError("candidate_ids must not be empty")
    build = _menu_model if mode == "menu" else _shopping_model
    model = build(Literal[tuple(candidate_ids)])
    if count_enum_values(to_strict_json_schema(model)) <= max_enum_values:
        return model
    return build(str)


def _shopping_model(product_id: Any) -> type[BaseModel]:
    line = create_model(
        "LLMLine",
        product_id=(product_id, ...),
        packs=(int, Field(ge=1, le=MAX_PACKS)),
    )
    return create_model("LLMShoppingPlan", lines=(list[line], ...), notes=(str, ...))


def _menu_model(product_id: Any) -> type[BaseModel]:
    ingredient = create_model(
        "LLMIngredient",
        product_id=(product_id, ...),
        amount_per_person=(float, Field(ge=MIN_PORTION, le=MAX_PORTION)),
    )
    meal = create_model(
        "LLMMeal",
        name=(str, ...),
        description=(str, ...),
        ingredients=(list[ingredient], ...),
    )
    day_menu = create_model(
        "LLMDayMenu",
        day=(str, ...),
        breakfast=(meal, ...),
        lunch=(meal, ...),
        dinner=(meal, ...),
        snack=(meal | None, ...),
    )
    return create_model("LLMMenuPlan", menu=(list[day_menu], ...), notes=(str, ...))
