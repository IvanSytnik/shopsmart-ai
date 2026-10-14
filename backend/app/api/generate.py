import logging
from typing import Annotated

import openai
from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI

from app.api.deps import get_llm_client, get_settings
from app.config import Settings
from app.schemas.requests import GenerateRequest
from app.schemas.responses import GenerateResponse
from app.services.llm import LLMOutputError
from app.services.planner import create_plan, to_response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    user_input: GenerateRequest,
    client: Annotated[AsyncOpenAI, Depends(get_llm_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> GenerateResponse:
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
        raise HTTPException(status_code=504, detail="AI service timed out") from None
    except openai.APIError:
        logger.exception("OpenAI request failed")
        raise HTTPException(status_code=503, detail="AI service unavailable") from None
    except LLMOutputError:
        logger.exception("LLM returned an unusable plan")
        raise HTTPException(status_code=502, detail="Failed to generate plan") from None
    except Exception:
        logger.exception("Unexpected error while generating plan")
        raise HTTPException(status_code=500, detail="Failed to generate plan") from None
