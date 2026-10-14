import logging
from typing import Annotated

import openai
from fastapi import APIRouter, Depends, Request
from openai import AsyncOpenAI

from app.api.deps import get_catalog, get_daily_cap, get_llm_client, get_settings
from app.config import Settings
from app.errors import AppError
from app.schemas.requests import GenerateRequest
from app.schemas.responses import GenerateResponse
from app.services.catalog import ProductCatalog
from app.services.limits import DailyCap, current_rate_limit, limiter
from app.services.llm import LLMOutputError
from app.services.planner import (
    NotEnoughProductsError,
    create_plan,
    select_candidates,
    to_response,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
@limiter.limit(current_rate_limit)
async def generate(
    request: Request,  # required by slowapi
    user_input: GenerateRequest,
    client: Annotated[AsyncOpenAI, Depends(get_llm_client)],
    settings: Annotated[Settings, Depends(get_settings)],
    daily_cap: Annotated[DailyCap, Depends(get_daily_cap)],
    catalog: Annotated[ProductCatalog, Depends(get_catalog)],
) -> GenerateResponse:
    # Request checks that need the catalog; before the daily cap so they don't use it up.
    known_stores = catalog.stores_by_country()[user_input.country]
    if unknown := [s for s in user_input.supermarkets if s not in known_stores]:
        logger.info("Unknown stores for %s: %s", user_input.country, unknown)
        raise AppError(422, "unknown_store", "Unknown store for the selected country")
    try:
        candidates = select_candidates(catalog, user_input)
    except NotEnoughProductsError as e:
        logger.info("Not enough products: %s", e)
        raise AppError(
            422, "not_enough_products", "Not enough products for these stores and diets"
        ) from None

    # Checked after the per-IP limit, so throttled requests don't use up the daily budget.
    if not daily_cap.try_acquire():
        logger.warning("Daily /generate cap of %d reached", daily_cap.cap)
        raise AppError(503, "daily_limit", "Daily limit reached, try tomorrow")

    logger.info(
        "Mode: %s, Budget: €%s, Family: %s, Candidates: %d",
        user_input.mode,
        user_input.budget,
        user_input.family_size,
        len(candidates),
    )
    try:
        result = await create_plan(client, settings, catalog, user_input, candidates)
        return to_response(result, user_input, catalog)
    except openai.APITimeoutError:
        logger.exception("OpenAI request timed out")
        raise AppError(504, "ai_timeout", "AI service timed out") from None
    except TimeoutError:
        logger.exception("Request deadline of %ss exceeded", settings.request_deadline_s)
        raise AppError(504, "ai_timeout", "AI service timed out") from None
    except openai.APIError:
        logger.exception("OpenAI request failed")
        raise AppError(503, "ai_unavailable", "AI service unavailable") from None
    except LLMOutputError:
        logger.exception("LLM returned an unusable plan")
        raise AppError(502, "generation_failed", "Failed to generate plan") from None
    except Exception:
        logger.exception("Unexpected error while generating plan")
        raise AppError(500, "generation_failed", "Failed to generate plan") from None
