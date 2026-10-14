import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api import generate, health
from app.config import Settings
from app.services.limits import DailyCap, configure_rate_limit, limiter
from app.services.llm import create_llm_client


async def rate_limited(request: Request, exc: Exception) -> JSONResponse:
    # slowapi already logs the exceeded limit with the client key.
    return JSONResponse(
        status_code=429, content={"detail": "Too many requests, please try again later"}
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.llm_client.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    app = FastAPI(title="ShopSmart AI API", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.llm_client = create_llm_client(settings)
    app.state.daily_cap = DailyCap(settings.daily_generate_cap)
    app.state.limiter = limiter
    configure_rate_limit(settings.rate_limit)
    app.add_exception_handler(RateLimitExceeded, rate_limited)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(generate.router)
    return app


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = create_app()
