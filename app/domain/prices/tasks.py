import asyncio

import aiohttp
from celery import shared_task
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.domain.prices.services import PriceCollectorService
from app.infrastructure.database.repositories.index_price_repository import IndexPriceRepository
from app.infrastructure.database.session import create_session_factory
from app.infrastructure.deribit.client import DeribitClient


@shared_task(name="prices.collect")
def collect_prices() -> None:
    """Celery has no native async tasks, so each run owns its event loop and resources."""
    asyncio.run(_collect_prices(Settings()))


async def _collect_prices(settings: Settings) -> None:
    engine = create_async_engine(settings.DATABASE.URL)
    timeout = aiohttp.ClientTimeout(total=settings.DERIBIT.TIMEOUT_SECONDS)
    try:
        async with (
            aiohttp.ClientSession(timeout=timeout) as http_session,
            create_session_factory(engine)() as db_session,
        ):
            collector = PriceCollectorService(
                client=DeribitClient(http_session, settings.DERIBIT.BASE_URL),
                repository=IndexPriceRepository(db_session),
            )
            await collector.collect()
            await db_session.commit()
    finally:
        await engine.dispose()
