"""
ShopSmart AI - Backend API
FastAPI server with OpenAI GPT-4 integration for intelligent shopping list generation.

Author: Ivan Sytnik (КН-М524)
Supervisor: Kharchenko A.O.
NTU "KhPI" - 2025
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import openai
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ShopSmart AI API",
    description="Intelligent shopping list generator powered by GPT-4",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
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


class AIResponse(BaseModel):
    items: List[ShoppingItem]
    total_cost: float
    notes: str
    generated_at: str


LANGUAGE_INSTRUCTIONS = {
    "en": "Respond in English. Use English product names.",
    "uk": "Відповідай українською мовою. Використовуй українські назви продуктів.",
    "de": "Antworte auf Deutsch. Verwende deutsche Produktnamen."
}

LANGUAGE_NOTES = {
    "en": "Shopping list optimized for your budget and preferences.",
    "uk": "Список покупок оптимізовано під ваш бюджет та вподобання.",
    "de": "Einkaufsliste für Ihr Budget und Ihre Vorlieben optimiert."
}


def get_system_prompt(language: str) -> str:
    lang_instruction = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])
    
    return f"""You are ShopSmart AI, an intelligent shopping assistant for German supermarkets.
{lang_instruction}

Your task is to create an optimized weekly shopping list based on:
- Selected supermarkets and their typical pricing
- User's budget (use 85-98% of it)
- Family size (adjust quantities accordingly)
- Dietary preferences and restrictions

Supermarket characteristics:
- Lidl: Budget-friendly, good basics, limited organic
- Aldi: Very affordable, quality basics, good weekly specials
- Edeka: Premium quality, wide organic selection, higher prices
- Rewe: Good quality, extensive range, moderate prices
- Kaufland: Large selection, competitive prices, bulk options

Categories to use: vegetables, fruits, meat, fish, dairy, bread, beverages, snacks, frozen, pantry, cleaning, hygiene

IMPORTANT: 
- Distribute items across selected stores based on best value
- Include variety for balanced nutrition
- Adjust portions for family size
- Stay within budget while maximizing value

Response format (JSON only, no markdown):
{{
  "items": [
    {{"product": "Product name", "quantity": "Amount", "store": "Store name", "approx_price": 0.00, "category": "category"}}
  ],
  "total_cost": 0.00,
  "notes": "Brief optimization notes"
}}"""


@app.get("/")
async def root():
    return {"message": "ShopSmart AI API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/generate", response_model=AIResponse)
async def generate_shopping_list(user_input: UserInput):
    try:
        logger.info(f"Generating list for budget €{user_input.budget}, family size {user_input.family_size}, language {user_input.language}")
        
        user_message = f"""Create a shopping list with these parameters:
- Supermarkets: {', '.join(user_input.supermarkets)}
- Weekly budget: €{user_input.budget}
- Family size: {user_input.family_size} people
- Preferences: {user_input.preferences if user_input.preferences else 'None specified'}

Generate 15-25 items optimized for value and nutrition."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": get_system_prompt(user_input.language)},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content
        logger.info(f"Raw response: {content[:200]}...")
        
        # Clean markdown if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        data = json.loads(content.strip())
        
        # Add notes in correct language if missing
        if not data.get("notes"):
            data["notes"] = LANGUAGE_NOTES.get(user_input.language, LANGUAGE_NOTES["en"])
        
        return AIResponse(
            items=data["items"],
            total_cost=data["total_cost"],
            notes=data["notes"],
            generated_at=datetime.now().isoformat()
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse AI response")
    except openai.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
