"""OpenAI access via Structured Outputs (`AsyncOpenAI` + `chat.completions.parse`)."""

import logging
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


@dataclass(frozen=True)
class TokenUsage:
    """Tokens of one completion call (for evals and cost estimates)."""

    prompt_tokens: int
    completion_tokens: int


def _usage_of(response: httpx.Response) -> CompletionUsage | None:
    try:
        usage = response.json().get("usage")
        return CompletionUsage.model_validate(usage) if usage else None
    except (ValueError, ValidationError):
        return None


def _record_usage(usage: CompletionUsage | None, usage_log: list[TokenUsage] | None) -> None:
    if usage is None:
        return
    logger.debug(
        "LLM usage: %d prompt + %d completion tokens", usage.prompt_tokens, usage.completion_tokens
    )
    if usage_log is not None:
        usage_log.append(TokenUsage(usage.prompt_tokens, usage.completion_tokens))


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
    usage_log: list[TokenUsage] | None = None,
) -> tuple[M, str | None]:
    """One completion call. Returns the reply parsed as `response_model` and its raw text.

    Token usage, when the API reports it, is appended to `usage_log` (also for unusable
    replies). Raises `LLMOutputError` for refusals, truncation, filtered or unparseable
    replies; `openai.APIError` (incl. `APITimeoutError`) propagates unchanged.
    """
    # The raw response gives the token usage before parsing, so it is recorded even when
    # the reply can't be parsed. API errors are raised by this call.
    raw = await client.chat.completions.with_raw_response.parse(
        model=settings.openai_model,
        messages=messages,
        response_format=response_model,
        temperature=settings.openai_temperature,
        max_completion_tokens=max_tokens,
    )
    _record_usage(_usage_of(raw.http_response), usage_log)
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
