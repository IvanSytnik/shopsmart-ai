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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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

class TotalNutrition(BaseModel):
    calories: int
    protein: float
    fat: float
    carbs: float

class AIResponse(BaseModel):
    items: List[ShoppingItem]
    total_cost: float
    notes: str
    generated_at: str
    total_nutrition: Optional[TotalNutrition] = None

LANG = {
    "en": ("Respond in English.", "Shopping list optimized for your budget."),
    "uk": ("Відповідай українською.", "Список оптимізовано під ваш бюджет."),
    "de": ("Antworte auf Deutsch.", "Einkaufsliste für Ihr Budget optimiert.")
}

def get_system_prompt(lang: str) -> str:
    instruction = LANG.get(lang, LANG["en"])[0]
    return f"""You are ShopSmart AI for German supermarkets. {instruction}

Create optimized weekly shopping list. Use 85-98% of budget.

Stores: Lidl/Aldi=budget, Edeka=premium, Rewe=mid-range, Kaufland=bulk.
Categories: vegetables, fruits, meat, fish, dairy, bread, beverages, snacks, frozen, pantry, cleaning, hygiene

For FOOD items, estimate nutrition (calories, protein, fat, carbs). Non-food = 0.

JSON format only:
{{"items":[{{"product":"Name","quantity":"Amount","store":"Store","approx_price":0.00,"category":"cat","calories":100,"protein":5.0,"fat":2.0,"carbs":15.0}}],"total_cost":0.00,"notes":"Brief notes","total_nutrition":{{"calories":5000,"protein":150.0,"fat":100.0,"carbs":400.0}}}}"""

@app.get("/")
async def root():
    return {"message": "ShopSmart AI API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/generate", response_model=AIResponse)
async def generate(user_input: UserInput):
    try:
        logger.info(f"Generating: €{user_input.budget}, {user_input.family_size} people, {user_input.language}")
        
        msg = f"Supermarkets: {', '.join(user_input.supermarkets)}\nBudget: €{user_input.budget}\nFamily: {user_input.family_size}\nPreferences: {user_input.preferences or 'None'}\n\nGenerate 15-25 items with nutrition."
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": get_system_prompt(user_input.language)}, {"role": "user", "content": msg}],
            temperature=0.7, max_tokens=3000
        )
        
        content = response.choices[0].message.content
        if "```json" in content: content = content.split("```json")[1].split("```")[0]
        elif "```" in content: content = content.split("```")[1].split("```")[0]
        
        data = json.loads(content.strip())
        
        if not data.get("notes"): data["notes"] = LANG.get(user_input.language, LANG["en"])[1]
        if not data.get("total_nutrition"):
            data["total_nutrition"] = {
                "calories": sum(i.get("calories", 0) for i in data["items"]),
                "protein": round(sum(i.get("protein", 0) for i in data["items"]), 1),
                "fat": round(sum(i.get("fat", 0) for i in data["items"]), 1),
                "carbs": round(sum(i.get("carbs", 0) for i in data["items"]), 1)
            }
        
        return AIResponse(items=data["items"], total_cost=data["total_cost"], notes=data["notes"], generated_at=datetime.now().isoformat(), total_nutrition=data.get("total_nutrition"))
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
