import logging
from typing import Annotated

import openai
from fastapi import APIRouter, Depends, Request
from openai import AsyncOpenAI

from app.api.deps import get_daily_cap, get_llm_client, get_settings
from app.config import Settings
from app.errors import AppError
from app.schemas.requests import GenerateRequest
from app.schemas.responses import GenerateResponse
from app.services.limits import DailyCap, current_rate_limit, limiter
from app.services.llm import LLMOutputError
from app.services.planner import create_plan, to_response

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
) -> GenerateResponse:
    # Checked after the per-IP limit, so throttled requests don't use up the daily budget.
    if not daily_cap.try_acquire():
        logger.warning("Daily /generate cap of %d reached", daily_cap.cap)
        raise AppError(503, "daily_limit", "Daily limit reached, try tomorrow")

    logger.info(
        "Mode: %s, Budget: €%s, Family: %s",
        user_input.mode,
        user_input.budget,
        user_input.family_size,
    )
    try:
        plan = await create_plan(client, settings, user_input)
        return to_response(plan, user_input.language)
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
