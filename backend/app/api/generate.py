import json
import logging
from typing import Annotated

import openai
from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI

from app.api.deps import get_llm_client, get_settings
from app.config import Settings
from app.schemas.llm import LLMPlan
from app.schemas.requests import GenerateRequest
from app.schemas.responses import GenerateResponse
from app.services.llm import complete_json
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
    try:
        logger.info(
            "Mode: %s, Budget: €%s, Family: %s",
            user_input.mode,
            user_input.budget,
            user_input.family_size,
        )
        system_prompt, user_message = build_messages(user_input)
        data = complete_json(client, settings, system_prompt, user_message)
        plan = LLMPlan.model_validate(data)
        return to_response(plan, user_input.language)

    except json.JSONDecodeError as e:
        logger.error(f"JSON error: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse AI response") from e
    except openai.APIError as e:
        logger.error(f"OpenAI error: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable") from e
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
