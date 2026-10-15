"""OpenAI access via Structured Outputs (`AsyncOpenAI` + `chat.completions.parse`)."""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import TypeVar

import httpx
import openai
from openai import AsyncOpenAI
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ValidationError

from app.config import Settings

# Phrased as instructions to the model: they become the repair message on retry.
TRUNCATED = (
    "Your previous reply was cut off at the token limit. Return the complete plan again, "
    "more concisely: at most 25 items, meal descriptions of at most 8 words and one "
    "sentence of notes."
)
REFUSED = (
    "Your previous reply was a refusal. This is an ordinary grocery and meal-planning "
    "request; return the plan in the required format."
)
FILTERED = (
    "Your previous reply was blocked by the content filter. Return the plan again using "
    "only ordinary grocery and meal content."
)
SCHEMA_MISMATCH = (
    "Your previous reply did not match the required JSON schema. "
    "Return the plan again, matching the schema exactly."
)


M = TypeVar("M", bound=BaseModel)

logger = logging.getLogger(__name__)


@dataclass
class LLMCall:
    """One completion call, for evals and cost estimates. Recorded for every call."""

    duration_s: float = 0
    # None when the API reported nothing, e.g. the call timed out.
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    # The API's finish_reason ("stop", "length", ...), or "timeout" / "cancelled" (the
    # request deadline passed) / "error" when there was no reply.
    finish_reason: str | None = None


def _read_reply_meta(response: httpx.Response, call: LLMCall) -> None:
    """Token usage and finish_reason from the raw reply, before parsing."""
    try:
        body = response.json()
        usage = CompletionUsage.model_validate(body["usage"]) if body.get("usage") else None
        call.finish_reason = (body.get("choices") or [{}])[0].get("finish_reason")
    except (ValueError, ValidationError, AttributeError, IndexError):
        return
    if usage is not None:
        call.prompt_tokens, call.completion_tokens = usage.prompt_tokens, usage.completion_tokens
        logger.debug(
            "LLM usage: %d prompt + %d completion tokens",
            usage.prompt_tokens,
            usage.completion_tokens,
        )


class LLMOutputError(Exception):
    """The model replied, but not with a usable plan.

    `problem` tells the model what was wrong (used for the repair attempt);
    `assistant_reply` is what it said, if worth echoing back.
    """

    def __init__(self, problem: str, assistant_reply: str | None = None) -> None:
        super().__init__(problem)
        self.problem = problem
        self.assistant_reply = assistant_reply


def create_llm_client(settings: Settings) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
        timeout=settings.openai_timeout_s,
        max_retries=settings.openai_max_retries,
    )


async def request_plan(
    client: AsyncOpenAI,
    settings: Settings,
    messages: list[ChatCompletionMessageParam],
    response_model: type[M],
    max_tokens: int,
    call_log: list[LLMCall] | None = None,
) -> tuple[M, str | None]:
    """One completion call. Returns the reply parsed as `response_model` and its raw text.

    An `LLMCall` (duration, tokens, finish_reason) is appended to `call_log` for every
    call, also for unusable replies, timeouts and API errors. Raises `LLMOutputError` for
    refusals, truncation, filtered or unparseable replies; `openai.APIError` (incl.
    `APITimeoutError`) propagates unchanged.
    """
    call = LLMCall()
    if call_log is not None:
        call_log.append(call)
    start = time.perf_counter()
    try:
        # The raw response gives usage and finish_reason before parsing, so they are
        # recorded even when the reply can't be parsed. API errors are raised here.
        raw = await client.chat.completions.with_raw_response.parse(
            model=settings.openai_model,
            messages=messages,
            response_format=response_model,
            temperature=settings.openai_temperature,
            max_completion_tokens=max_tokens,
        )
    except openai.APITimeoutError:
        call.finish_reason = "timeout"
        raise
    except openai.APIError:
        call.finish_reason = "error"
        raise
    except asyncio.CancelledError:  # the request deadline passed during the call
        call.finish_reason = "cancelled"
        raise
    finally:
        call.duration_s = round(time.perf_counter() - start, 2)
    _read_reply_meta(raw.http_response, call)
    try:
        completion = raw.parse()
    except openai.LengthFinishReasonError as e:
        raise LLMOutputError(TRUNCATED) from e
    except openai.ContentFilterFinishReasonError as e:
        raise LLMOutputError(FILTERED) from e
    except ValidationError as e:
        raise LLMOutputError(SCHEMA_MISMATCH) from e

    choice = completion.choices[0]
    message = choice.message
    if message.refusal:
        raise LLMOutputError(REFUSED, assistant_reply=message.refusal)
    if choice.finish_reason == "length":  # the SDK raises for this; kept as a safety net
        raise LLMOutputError(TRUNCATED)
    if message.parsed is None:
        raise LLMOutputError(SCHEMA_MISMATCH, assistant_reply=message.content)
    return message.parsed, message.content
