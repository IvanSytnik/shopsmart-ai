import logging
from typing import Annotated

import openai
from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI

from app.api.deps import get_llm_client, get_settings
from app.config import Settings
from app.schemas.requests import GenerateRequest
from app.schemas.responses import GenerateResponse
from app.services.llm import LLMOutputError, generate_plan
from app.services.planner import build_messages, to_response

logger = logging.getLogger(__name__)

router = APIRouter()


# Plain `def`: the sync OpenAI client runs in FastAPI's threadpool instead of
# blocking the event loop. Becomes `async def` with AsyncOpenAI in Phase 1.2.
@router.post("/generate", response_model=GenerateResponse)
def generate(
    user_input: GenerateRequest,
    client: Annotated[OpenAI, Depends(get_llm_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> GenerateResponse:
    logger.info(
        "Mode: %s, Budget: €%s, Family: %s",
        user_input.mode,
        user_input.budget,
        user_input.family_size,
    )
    try:
        system_prompt, user_message = build_messages(user_input)
        plan = generate_plan(client, settings, system_prompt, user_message)
        return to_response(plan, user_input.language)
    except openai.APIError:
        logger.exception("OpenAI request failed")
        raise HTTPException(status_code=503, detail="AI service unavailable") from None
    except LLMOutputError:
        logger.exception("LLM returned an unusable plan")
        raise HTTPException(status_code=502, detail="Failed to generate plan") from None
    except Exception:
        logger.exception("Unexpected error while generating plan")
        raise HTTPException(status_code=500, detail="Failed to generate plan") from None
