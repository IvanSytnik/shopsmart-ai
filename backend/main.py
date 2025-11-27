"""
ShopSmart AI - Backend API
Author: Ivan Sytnik (КН-М524)
Supervisor: Kharchenko A.O.
NTU "KhPI" - 2025
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import openai
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="ShopSmart AI API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class UserInput(BaseModel):
    supermarkets: List[str]
    budget: float = Field(gt=0, le=10000)
    preferences: str = ""
    family_size: int = Field(ge=1, le=20, default=2)
    language: str = "en"
    mode: str = "shopping"
    days: Optional[int] = 7

class Meal(BaseModel):
    name: str
    description: str
    calories: Optional[int] = None

class DayMenu(BaseModel):
    day: str
    breakfast: Meal
    lunch: Meal
    dinner: Meal
    snack: Optional[Meal] = None

class ShoppingItem(BaseModel):
    product: str
    quantity: str
    store: str
    approx_price: float
    category: str
    calories: Optional[int] = 0
    protein: Optional[float] = 0
    fat: Optional[float] = 0
    carbs: Optional[float] = 0

class AIResponse(BaseModel):
    items: List[ShoppingItem]
    total_cost: float
    notes: str
    generated_at: str
    menu: Optional[List[DayMenu]] = None

LANG = {
    "en": ("Respond in English.", "Shopping list optimized for your budget."),
    "uk": ("Відповідай українською.", "Список оптимізовано під ваш бюджет."),
    "de": ("Antworte auf Deutsch.", "Einkaufsliste für Ihr Budget optimiert.")
}

DAY_NAMES = {
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "uk": ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"],
    "de": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
}

def get_shopping_prompt(lang: str) -> str:
    instruction = LANG.get(lang, LANG["en"])[0]
    return f"""You are ShopSmart AI for German supermarkets. {instruction}

Create optimized weekly shopping list. Use 85-98% of budget.
Stores: Lidl/Aldi=budget, Edeka=premium, Rewe=mid-range, Kaufland=bulk.
Categories: vegetables, fruits, meat, fish, dairy, bread, beverages, snacks, frozen, pantry, cleaning, hygiene

For FOOD items, estimate nutrition. Non-food = 0.

JSON only:
{{"items":[{{"product":"Name","quantity":"Amount","store":"Store","approx_price":0.00,"category":"cat","calories":100,"protein":5.0,"fat":2.0,"carbs":15.0}}],"total_cost":0.00,"notes":"Brief notes"}}"""

def get_menu_prompt(lang: str, days: int) -> str:
    instruction = LANG.get(lang, LANG["en"])[0]
    day_names = DAY_NAMES.get(lang, DAY_NAMES["en"])[:days]
    
    return f"""You are ShopSmart AI meal planner. {instruction}

Create a {days}-day meal plan with breakfast, lunch, dinner, and snack for each day.
Then create a shopping list with all needed products.

Days: {', '.join(day_names)}

Consider: balanced nutrition, variety, budget optimization.

JSON only:
{{"menu":[{{"day":"Day name","breakfast":{{"name":"Meal","description":"Short description","calories":300}},"lunch":{{"name":"Meal","description":"Description","calories":500}},"dinner":{{"name":"Meal","description":"Description","calories":600}},"snack":{{"name":"Snack","description":"Description","calories":150}}}}],"items":[{{"product":"Name","quantity":"Amount","store":"Store","approx_price":0.00,"category":"cat","calories":100,"protein":5.0,"fat":2.0,"carbs":15.0}}],"total_cost":0.00,"notes":"Brief notes"}}"""

@app.get("/")
async def root():
    return {"message": "ShopSmart AI API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/generate", response_model=AIResponse)
async def generate(user_input: UserInput):
    try:
        logger.info(f"Mode: {user_input.mode}, Budget: €{user_input.budget}, Family: {user_input.family_size}")
        
        if user_input.mode == "menu":
            system_prompt = get_menu_prompt(user_input.language, user_input.days or 7)
            user_msg = f"Supermarkets: {', '.join(user_input.supermarkets)}\nBudget: €{user_input.budget}\nFamily: {user_input.family_size}\nPreferences: {user_input.preferences or 'None'}\n\nCreate {user_input.days}-day meal plan with shopping list."
        else:
            system_prompt = get_shopping_prompt(user_input.language)
            user_msg = f"Supermarkets: {', '.join(user_input.supermarkets)}\nBudget: €{user_input.budget}\nFamily: {user_input.family_size}\nPreferences: {user_input.preferences or 'None'}\n\nGenerate 15-25 items."
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_msg}],
            temperature=0.7,
            max_tokens=4000
        )
        
        content = response.choices[0].message.content
        if "```json" in content: content = content.split("```json")[1].split("```")[0]
        elif "```" in content: content = content.split("```")[1].split("```")[0]
        
        data = json.loads(content.strip())
        
        if not data.get("notes"):
            data["notes"] = LANG.get(user_input.language, LANG["en"])[1]
        
        return AIResponse(
            items=data.get("items", []),
            total_cost=data.get("total_cost", 0),
            notes=data.get("notes", ""),
            generated_at=datetime.now().isoformat(),
            menu=data.get("menu")
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON error: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse AI response")
    except openai.APIError as e:
        logger.error(f"OpenAI error: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
