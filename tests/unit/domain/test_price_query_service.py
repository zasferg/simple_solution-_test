from decimal import Decimal

import pytest

from app.domain.prices.exceptions import InvalidDateRangeError, PriceNotFoundError
from app.domain.prices.schemas import IndexPrice
from app.domain.prices.services import PriceQueryService
from app.domain.prices.types import Ticker
from tests.fakes import InMemoryPriceRepository


def make_price(timestamp: int, ticker: Ticker = Ticker.BTC_USD) -> IndexPrice:
    return IndexPrice(ticker=ticker, price=Decimal(timestamp), timestamp=timestamp)


async def test_get_latest_returns_most_recent_price_of_ticker() -> None:
    repository = InMemoryPriceRepository(
        [make_price(10), make_price(30), make_price(20), make_price(99, Ticker.ETH_USD)]
    )

    latest = await PriceQueryService(repository).get_latest(Ticker.BTC_USD)

    assert latest == make_price(30)


async def test_get_latest_without_data_raises_not_found() -> None:
    with pytest.raises(PriceNotFoundError):
        await PriceQueryService(InMemoryPriceRepository()).get_latest(Ticker.BTC_USD)


async def test_find_applies_date_range_and_pagination() -> None:
    repository = InMemoryPriceRepository([make_price(timestamp) for timestamp in range(10, 70, 10)])

    found = await PriceQueryService(repository).find(Ticker.BTC_USD, limit=2, offset=1, date_from=20, date_to=50)

    assert found == [make_price(30), make_price(40)]


async def test_find_rejects_reversed_date_range() -> None:
    with pytest.raises(InvalidDateRangeError):
        await PriceQueryService(InMemoryPriceRepository()).find(
            Ticker.BTC_USD, limit=10, offset=0, date_from=20, date_to=10
        )
