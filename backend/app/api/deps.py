from fastapi import Request
from openai import AsyncOpenAI

from app.config import Settings
from app.services.limits import DailyCap


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_llm_client(request: Request) -> AsyncOpenAI:
    """The single OpenAI client created in `create_app`; override in tests."""
    return request.app.state.llm_client


def get_daily_cap(request: Request) -> DailyCap:
    return request.app.state.daily_cap
