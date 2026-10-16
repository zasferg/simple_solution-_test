from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.infrastructure.database.session import create_session_factory
from app.infrastructure.errors.base import BaseError
from app.infrastructure.errors.handlers import base_error_handler
from app.presentation.api import healthchecks
from app.presentation.api.v1.prices.endpoints import router as prices_router_v1


def create_app(settings: Settings) -> FastAPI:
    """Build the HTTP application; the database engine lives for the application's lifespan."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_async_engine(settings.DATABASE.URL)
        app.state.session_factory = create_session_factory(engine)
        yield
        await engine.dispose()

    app = FastAPI(title="Deribit price tracker", lifespan=lifespan)
    app.include_router(healthchecks.router)
    app.include_router(prices_router_v1, prefix="/v1")
    app.add_exception_handler(BaseError, base_error_handler)
    return app
