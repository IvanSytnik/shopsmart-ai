"""
ShopSmart AI - Backend API
FastAPI server with OpenAI GPT-4 integration for intelligent shopping list generation.

Author: Ivan Sytnyk (КН-М524)
Supervisor: Kharchenko A.O.
NTU "KhPI" - 2025
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"  # Allow all origins in development
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== Pydantic Models ==============

class UserInput(BaseModel):
    """User input for shopping list generation"""
    supermarkets: List[str] = Field(
        ..., 
        min_items=1, 
        max_items=5,
        description="List of selected supermarkets",
        example=["Lidl", "Aldi", "Edeka"]
    )
    budget: float = Field(
        ..., 
        gt=0, 
        le=1000,
        description="Weekly budget in EUR",
        example=50.0
    )
    preferences: Optional[str] = Field(
        None, 
        max_length=500,
        description="User dietary preferences and restrictions",
        example="vegetarian, prefer organic vegetables"
    )
    family_size: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Number of people in the family",
        example=2
    )

    @validator('supermarkets')
    def validate_supermarkets(cls, v):
        valid_markets = {'Lidl', 'Aldi', 'Edeka', 'Rewe', 'Kaufland'}
        for market in v:
            if market not in valid_markets:
                raise ValueError(f"Invalid supermarket: {market}. Valid options: {valid_markets}")
        return v

    class Config:
        schema_extra = {
            "example": {
                "supermarkets": ["Lidl", "Aldi"],
                "budget": 50.0,
                "preferences": "vegetarian diet",
                "family_size": 2
            }
        }


class ShoppingItem(BaseModel):
    """Single item in the shopping list"""
    product: str = Field(..., description="Product name")
    quantity: str = Field(..., description="Quantity with unit")
    store: str = Field(..., description="Recommended store")
    approx_price: str = Field(..., description="Approximate price in EUR")
    category: str = Field(..., description="Product category")

    class Config:
        schema_extra = {
            "example": {
                "product": "Organic Milk",
                "quantity": "1L",
                "store": "Lidl",
                "approx_price": "1.29",
                "category": "dairy"
            }
        }


class AIResponse(BaseModel):
    """Response from AI with shopping list"""
    items: List[ShoppingItem]
    total_cost: float = Field(..., description="Total estimated cost")
    notes: Optional[str] = Field(None, description="Additional notes and tips")
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    class Config:
        schema_extra = {
            "example": {
                "items": [
                    {
                        "product": "Organic Milk",
                        "quantity": "1L",
                        "store": "Lidl",
                        "approx_price": "1.29",
                        "category": "dairy"
                    }
                ],
                "total_cost": 45.50,
                "notes": "Consider buying seasonal vegetables for better prices."
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: str


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: str
    timestamp: str


# ============== OpenAI Configuration ==============

# Initialize OpenAI client
openai_api_key = os.getenv("OPENAI_API_KEY", "")
if openai_api_key:
    openai.api_key = openai_api_key
    logger.info("OpenAI API key configured successfully")
else:
    logger.warning("OPENAI_API_KEY not found in environment variables")


def create_shopping_prompt(data: UserInput) -> str:
    """Create the prompt for GPT-4"""
    supermarkets_str = ", ".join(data.supermarkets)
    preferences_str = f"\n- User preferences: {data.preferences}" if data.preferences else ""
    
    prompt = f"""You are ShopSmart AI, an expert shopping assistant for German supermarkets.

Generate an optimized weekly shopping list with these parameters:
- Available supermarkets: {supermarkets_str}
- Weekly budget: €{data.budget}
- Family size: {data.family_size} person(s){preferences_str}

IMPORTANT RULES:
1. Total cost must stay within budget (aim for 85-98% utilization)
2. Distribute items based on typical German supermarket pricing:
   - Lidl & Aldi: Discount prices, good for basics, dairy, frozen foods, pantry items
   - Edeka: Premium quality, best for fresh produce, meats, specialty items
   - Rewe: Good variety, quality products, slightly higher prices
   - Kaufland: Large selection, medium prices, good for bulk items
3. Include nutritionally balanced items:
   - Proteins (meat, fish, eggs, legumes)
   - Carbohydrates (bread, pasta, rice, potatoes)
   - Vegetables (fresh and frozen)
   - Fruits (fresh and frozen)
   - Dairy products
   - Pantry staples
4. Adjust portions for {data.family_size} person(s) for one week
5. Each item must be assigned to ONE of the selected supermarkets only
6. Use realistic German supermarket prices (2024-2025)

RESPONSE FORMAT:
Return ONLY a valid JSON object (no markdown, no explanations, no code blocks):
{{
  "items": [
    {{
      "product": "Product Name in English",
      "quantity": "amount with unit (e.g., 1kg, 500g, 6 pcs, 1L, 250g)",
      "store": "Exact store name from the list",
      "approx_price": "0.00",
      "category": "one of: vegetables, fruits, meat, fish, dairy, bread, beverages, snacks, frozen, pantry, cleaning, hygiene"
    }}
  ],
  "total_cost": 0.00,
  "notes": "1-2 sentences with shopping tips"
}}

Generate 15-25 items for a complete weekly shopping. Prices must be realistic.
The sum of all item prices must equal total_cost."""

    return prompt


def parse_ai_response(content: str) -> dict:
    """Parse and validate AI response"""
    # Remove markdown code blocks if present
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line (```)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)
    
    # Remove any remaining backticks
    content = content.replace("```json", "").replace("```", "").strip()
    
    try:
        result = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.error(f"Content: {content[:500]}...")
        raise ValueError(f"Invalid JSON response from AI: {str(e)}")
    
    # Validate required fields
    if "items" not in result:
        raise ValueError("Missing 'items' in AI response")
    if "total_cost" not in result:
        # Calculate total if missing
        total = sum(float(item.get("approx_price", 0)) for item in result["items"])
        result["total_cost"] = round(total, 2)
    
    return result


async def generate_shopping_list(data: UserInput) -> AIResponse:
    """Generate shopping list using GPT-4"""
    
    if not openai.api_key:
        raise HTTPException(
            status_code=500, 
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
        )
    
    prompt = create_shopping_prompt(data)
    
    logger.info(f"Generating shopping list for budget €{data.budget}, stores: {data.supermarkets}")
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",  # Cost-effective model with good performance
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful shopping assistant. Return only valid JSON, no markdown or explanations."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3000,
            response_format={"type": "json_object"}  # Force JSON response
        )
        
        content = response.choices[0].message.content.strip()
        logger.info(f"Received response from OpenAI ({len(content)} chars)")
        
        result = parse_ai_response(content)
        
        # Add timestamp
        result["generated_at"] = datetime.now().isoformat()
        
        logger.info(f"Generated {len(result['items'])} items, total: €{result['total_cost']}")
        
        return AIResponse(**result)
        
    except openai.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {str(e)}")
    except openai.RateLimitError as e:
        logger.error(f"OpenAI rate limit: {e}")
        raise HTTPException(status_code=429, detail="API rate limit exceeded. Please try again later.")
    except ValueError as e:
        logger.error(f"Response parsing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ============== API Endpoints ==============

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "ShopSmart AI API",
        "version": "1.0.0",
        "description": "Intelligent shopping list generator powered by GPT-4",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )


@app.get("/api/supermarkets", tags=["Data"])
async def get_supermarkets():
    """Get list of available supermarkets"""
    return {
        "supermarkets": [
            {"id": "lidl", "name": "Lidl", "type": "discount", "color": "#0050aa"},
            {"id": "aldi", "name": "Aldi", "type": "discount", "color": "#00005f"},
            {"id": "edeka", "name": "Edeka", "type": "premium", "color": "#fff000"},
            {"id": "rewe", "name": "Rewe", "type": "standard", "color": "#cc0000"},
            {"id": "kaufland", "name": "Kaufland", "type": "hypermarket", "color": "#e30613"}
        ]
    }


@app.get("/api/categories", tags=["Data"])
async def get_categories():
    """Get list of product categories"""
    return {
        "categories": [
            {"id": "vegetables", "name": "Vegetables", "icon": "🥬"},
            {"id": "fruits", "name": "Fruits", "icon": "🍎"},
            {"id": "meat", "name": "Meat", "icon": "🥩"},
            {"id": "fish", "name": "Fish", "icon": "🐟"},
            {"id": "dairy", "name": "Dairy", "icon": "🥛"},
            {"id": "bread", "name": "Bread & Bakery", "icon": "🍞"},
            {"id": "beverages", "name": "Beverages", "icon": "🥤"},
            {"id": "snacks", "name": "Snacks", "icon": "🍪"},
            {"id": "frozen", "name": "Frozen Foods", "icon": "🧊"},
            {"id": "pantry", "name": "Pantry", "icon": "🥫"},
            {"id": "cleaning", "name": "Cleaning", "icon": "🧹"},
            {"id": "hygiene", "name": "Hygiene", "icon": "🧴"}
        ]
    }


@app.post("/generate", response_model=AIResponse, tags=["Generation"])
async def generate(data: UserInput):
    """
    Generate an optimized shopping list based on user preferences.
    
    - **supermarkets**: List of selected supermarkets (1-5)
    - **budget**: Weekly budget in EUR (1-1000)
    - **preferences**: Optional dietary preferences
    - **family_size**: Number of people (1-10)
    """
    logger.info(f"Received generation request: {data.dict()}")
    
    try:
        result = await generate_shopping_list(data)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate", response_model=AIResponse, tags=["Generation"])
async def generate_api(data: UserInput):
    """Alternative endpoint with /api prefix"""
    return await generate(data)


# ============== Error Handlers ==============

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Request failed",
            "detail": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


# ============== Main Entry Point ==============

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting ShopSmart AI API on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
