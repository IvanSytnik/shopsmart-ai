"""OpenAI access.

Still the sync client + `chat.completions.create()` with fence stripping, as in v1.
Phase 1.2 replaces this with `AsyncOpenAI` + `chat.completions.parse()`.
"""

import json
from typing import Any

from openai import OpenAI

from app.config import Settings


def create_llm_client(settings: Settings) -> OpenAI:
    return OpenAI(api_key=settings.openai_api_key.get_secret_value())


def complete_json(client: OpenAI, settings: Settings, system_prompt: str, user_message: str) -> Any:
    """Send the prompt and return the decoded JSON body of the reply."""
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=settings.openai_temperature,
        max_tokens=settings.openai_max_tokens,
    )

    content = response.choices[0].message.content
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    return json.loads(content.strip())
