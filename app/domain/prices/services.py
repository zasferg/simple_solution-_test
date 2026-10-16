import asyncio
import logging
import time
from collections.abc import Callable

from app.domain.prices.exceptions import InvalidDateRangeError, PriceFetchError, PriceNotFoundError
from app.domain.prices.interfaces import PriceClient, PriceRepository
from app.domain.prices.schemas import IndexPrice
from app.domain.prices.types import Ticker

logger = logging.getLogger(__name__)


class PriceCollectorService:
    """Fetches every ticker concurrently and stores the ones that succeeded."""

    def __init__(
        self,
        client: PriceClient,
        repository: PriceRepository,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._client = client
        self._repository = repository
        self._clock = clock

    async def collect(self) -> None:
        """
        Store one price per ticker, all with the same timestamp.

        A ticker whose price could not be fetched is skipped and logged; any other
        exception is a bug and is re-raised.
        """
        tickers = tuple(Ticker)
        results = await asyncio.gather(
            *(self._client.fetch_index_price(ticker) for ticker in tickers),
            return_exceptions=True,
        )
        timestamp = int(self._clock())
        prices: list[IndexPrice] = []
        for ticker, result in zip(tickers, results, strict=True):
            if isinstance(result, PriceFetchError):
                logger.warning("Skipping %s: %s", ticker, result)
            elif isinstance(result, BaseException):
                raise result
            else:
                prices.append(IndexPrice(ticker=ticker, price=result, timestamp=timestamp))
        await self._repository.add_many(prices)
        logger.info("Stored %d of %d index prices at %d", len(prices), len(tickers), timestamp)


class PriceQueryService:
    """Read access to stored prices for the API."""

    def __init__(self, repository: PriceRepository) -> None:
        self._repository = repository

    async def get_latest(self, ticker: Ticker) -> IndexPrice:
        price = await self._repository.get_latest(ticker)
        if price is None:
            raise PriceNotFoundError(ticker)
        return price

    async def find(
        self,
        ticker: Ticker,
        *,
        limit: int,
        offset: int,
        date_from: int | None = None,
        date_to: int | None = None,
    ) -> list[IndexPrice]:
        if date_from is not None and date_to is not None and date_from > date_to:
            raise InvalidDateRangeError
        return await self._repository.find(
            ticker,
            limit=limit,
            offset=offset,
            date_from=date_from,
            date_to=date_to,
        )
