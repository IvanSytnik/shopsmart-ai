import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import catalog, generate, health
from app.config import Settings
from app.errors import register_error_handlers
from app.services.catalog import load_catalog
from app.services.limits import DailyCap, configure_rate_limit, limiter
from app.services.llm import create_llm_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.llm_client.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    app = FastAPI(title="ShopSmart AI API", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.catalog = load_catalog(settings.catalog_path)  # fails fast on a bad file
    app.state.llm_client = create_llm_client(settings)
    app.state.daily_cap = DailyCap(settings.daily_generate_cap)
    app.state.limiter = limiter
    configure_rate_limit(settings.rate_limit)
    register_error_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(generate.router)
    app.include_router(catalog.router)
    return app


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = create_app()
