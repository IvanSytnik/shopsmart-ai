from fastapi import Request
from openai import AsyncOpenAI

from app.config import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_llm_client(request: Request) -> AsyncOpenAI:
    """The single OpenAI client created in `create_app`; override in tests."""
    return request.app.state.llm_client
