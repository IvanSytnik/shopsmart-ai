"""Prompt building and mapping of LLM output to the API response (moved as-is from v1)."""

from datetime import datetime

from app.schemas.llm import LLMPlan
from app.schemas.requests import GenerateRequest
from app.schemas.responses import GenerateResponse

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
        system_prompt = get_menu_prompt(request.language, request.days or 7)
        user_message = context + f"Create {request.days}-day meal plan with shopping list."
    else:
        system_prompt = get_shopping_prompt(request.language)
        user_message = context + "Generate 15-25 items."
    return system_prompt, user_message


def to_response(plan: LLMPlan, language: str) -> GenerateResponse:
    notes = plan.notes or LANG.get(language, LANG["en"])[1]
    return GenerateResponse.model_validate(
        {
            "items": [item.model_dump() for item in plan.items],
            "total_cost": plan.total_cost,
            "notes": notes,
            "generated_at": datetime.now().isoformat(),
            "menu": [day.model_dump() for day in plan.menu] if plan.menu is not None else None,
        }
    )
