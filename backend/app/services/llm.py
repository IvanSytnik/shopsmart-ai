"""OpenAI access via Structured Outputs (`AsyncOpenAI` + `chat.completions.parse`)."""

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import ValidationError

from app.config import Settings
from app.schemas.llm import LLMPlan

# Phrased as instructions to the model: they become the repair message on retry.
TRUNCATED = (
    "Your previous reply was cut off at the token limit. Return the complete plan again, "
    "more concisely: at most 25 items and one short sentence per meal description."
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
    client: AsyncOpenAI, settings: Settings, messages: list[ChatCompletionMessageParam]
) -> tuple[LLMPlan, str | None]:
    """One completion call. Returns the parsed plan and the raw reply text.

    Raises `LLMOutputError` for refusals, truncation, filtered or unparseable replies;
    `openai.APIError` (incl. `APITimeoutError`) propagates unchanged.
    """
    try:
        completion = await client.chat.completions.parse(
            model=settings.openai_model,
            messages=messages,
            response_format=LLMPlan,
            temperature=settings.openai_temperature,
            max_completion_tokens=settings.openai_max_tokens,
        )
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
