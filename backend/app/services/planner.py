"""Prompt building, the repair loop, and mapping of LLM output to the API response."""

import logging
from datetime import datetime

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.config import Settings
from app.schemas.llm import LLMPlan
from app.schemas.requests import GenerateRequest
from app.schemas.responses import GenerateResponse
from app.services.llm import LLMOutputError, request_plan

logger = logging.getLogger(__name__)

# First call + one repair retry. API errors are not retried here (the SDK has its own retries).
MAX_ATTEMPTS = 2
NUTRITION_FIELDS = ("calories", "protein", "fat", "carbs")

LANG = {
    "en": ("Respond in English.", "Shopping list optimized for your budget."),
    "uk": ("Відповідай українською.", "Список оптимізовано під ваш бюджет."),
    "de": ("Antworte auf Deutsch.", "Einkaufsliste für Ihr Budget optimiert."),
}

DAY_NAMES = {
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "uk": ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"],
    "de": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
}

_CATEGORIES = (
    "vegetables, fruits, meat, fish, dairy, bread, beverages, "
    "snacks, frozen, pantry, cleaning, hygiene"
)

# JSON examples embedded in the prompts; split only to keep lines short.
_ITEM_EXAMPLE = (
    '{"product":"Name","quantity":"Amount","store":"Store","approx_price":0.00,'
    '"category":"cat","calories":100,"protein":5.0,"fat":2.0,"carbs":15.0}'
)
_DAY_EXAMPLE = (
    '{"day":"Day name",'
    '"breakfast":{"name":"Meal","description":"Short description","calories":300},'
    '"lunch":{"name":"Meal","description":"Description","calories":500},'
    '"dinner":{"name":"Meal","description":"Description","calories":600},'
    '"snack":{"name":"Snack","description":"Description","calories":150}}'
)


def get_shopping_prompt(lang: str) -> str:
    instruction = LANG.get(lang, LANG["en"])[0]
    return f"""You are ShopSmart AI for German supermarkets. {instruction}

Create optimized weekly shopping list. Use 85-98% of budget.
Stores: Lidl/Aldi=budget, Edeka=premium, Rewe=mid-range, Kaufland=bulk.
Categories: {_CATEGORIES}

For FOOD items, estimate nutrition. Non-food = 0.

JSON only:
{{"items":[{_ITEM_EXAMPLE}],"total_cost":0.00,"notes":"Brief notes"}}"""


def get_menu_prompt(lang: str, days: int) -> str:
    instruction = LANG.get(lang, LANG["en"])[0]
    day_names = DAY_NAMES.get(lang, DAY_NAMES["en"])[:days]

    return f"""You are ShopSmart AI meal planner. {instruction}

Create a {days}-day meal plan with breakfast, lunch, dinner, and snack for each day.
Then create a shopping list with all needed products.

Days: {", ".join(day_names)}

Consider: balanced nutrition, variety, budget optimization.

JSON only:
{{"menu":[{_DAY_EXAMPLE}],"items":[{_ITEM_EXAMPLE}],"total_cost":0.00,"notes":"Brief notes"}}"""


def build_messages(request: GenerateRequest) -> tuple[str, str]:
    """Return (system_prompt, user_message) for the request."""
    context = (
        f"Supermarkets: {', '.join(request.supermarkets)}\n"
        f"Budget: €{request.budget}\n"
        f"Family: {request.family_size}\n"
        f"Preferences: {request.preferences or 'None'}\n\n"
    )
    if request.mode == "menu":
        system_prompt = get_menu_prompt(request.language, request.days)
        user_message = context + f"Create {request.days}-day meal plan with shopping list."
    else:
        system_prompt = get_shopping_prompt(request.language)
        user_message = context + "Generate 15-25 items."
    return system_prompt, user_message


def find_plan_problem(plan: LLMPlan, request: GenerateRequest) -> str | None:
    """Business checks on a schema-valid plan; returns a repair instruction or None."""
    if not plan.items:
        return (
            "Your previous reply had an empty `items` list. "
            "Include every product the household needs to buy."
        )
    if request.mode == "menu":
        names = ", ".join(DAY_NAMES.get(request.language, DAY_NAMES["en"])[: request.days])
        if plan.menu is None:
            return (
                f"Your previous reply had no `menu`. "
                f"Return a menu with exactly {request.days} days: {names}."
            )
        if len(plan.menu) != request.days:
            return (
                f"Your previous reply had {len(plan.menu)} days in `menu`, "
                f"but exactly {request.days} are required: {names}."
            )
    return None


async def create_plan(client: AsyncOpenAI, settings: Settings, request: GenerateRequest) -> LLMPlan:
    """Ask for a plan; on an unusable reply, retry once with a message saying what was wrong.

    Raises `LLMOutputError` if the repair attempt fails too.
    """
    system_prompt, user_message = build_messages(request)
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            plan, raw_reply = await request_plan(client, settings, messages)
            problem = find_plan_problem(plan, request)
            if problem is not None:
                raise LLMOutputError(problem, assistant_reply=raw_reply)
        except LLMOutputError as e:
            logger.warning("LLM attempt %d/%d unusable: %s", attempt, MAX_ATTEMPTS, e.problem)
            if attempt == MAX_ATTEMPTS:
                raise
            messages = [
                *messages,
                {"role": "assistant", "content": e.assistant_reply or "(reply omitted)"},
                {"role": "user", "content": e.problem},
            ]
        else:
            logger.info("LLM plan accepted on attempt %d/%d", attempt, MAX_ATTEMPTS)
            return plan
    raise AssertionError("unreachable")


def to_response(plan: LLMPlan, language: str) -> GenerateResponse:
    notes = plan.notes or LANG.get(language, LANG["en"])[1]
    items = []
    for item in plan.items:
        data = item.model_dump()
        # The API keeps v1's contract: missing nutrition is 0, not null.
        for field in NUTRITION_FIELDS:
            data[field] = data[field] or 0
        items.append(data)
    return GenerateResponse.model_validate(
        {
            "items": items,
            "total_cost": plan.total_cost,
            "notes": notes,
            "generated_at": datetime.now().isoformat(),
            "menu": [day.model_dump() for day in plan.menu] if plan.menu is not None else None,
        }
    )
