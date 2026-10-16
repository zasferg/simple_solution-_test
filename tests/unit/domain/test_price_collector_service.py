from decimal import Decimal

import pytest

from app.domain.prices.exceptions import PriceFetchError
from app.domain.prices.schemas import IndexPrice
from app.domain.prices.services import PriceCollectorService
from app.domain.prices.types import Ticker
from tests.fakes import FakePriceClient, InMemoryPriceRepository

NOW = 1_700_000_000.7


async def test_stores_every_ticker_with_one_timestamp() -> None:
    client = FakePriceClient({Ticker.BTC_USD: Decimal("83366.25"), Ticker.ETH_USD: Decimal("2503.92")})
    repository = InMemoryPriceRepository()

    await PriceCollectorService(client, repository, clock=lambda: NOW).collect()

    assert repository.prices == [
        IndexPrice(ticker=Ticker.BTC_USD, price=Decimal("83366.25"), timestamp=1_700_000_000),
        IndexPrice(ticker=Ticker.ETH_USD, price=Decimal("2503.92"), timestamp=1_700_000_000),
    ]


async def test_failed_ticker_does_not_block_others() -> None:
    client = FakePriceClient({Ticker.BTC_USD: Decimal("83366.25"), Ticker.ETH_USD: PriceFetchError("boom")})
    repository = InMemoryPriceRepository()

    await PriceCollectorService(client, repository, clock=lambda: NOW).collect()

    assert repository.prices == [IndexPrice(ticker=Ticker.BTC_USD, price=Decimal("83366.25"), timestamp=1_700_000_000)]


async def test_nothing_is_stored_when_every_ticker_fails() -> None:
    client = FakePriceClient({ticker: PriceFetchError("down") for ticker in Ticker})
    repository = InMemoryPriceRepository()

    await PriceCollectorService(client, repository, clock=lambda: NOW).collect()

    assert repository.prices == []


async def test_unexpected_error_is_raised() -> None:
    client = FakePriceClient({Ticker.BTC_USD: Decimal("1"), Ticker.ETH_USD: RuntimeError("bug")})
    service = PriceCollectorService(client, InMemoryPriceRepository(), clock=lambda: NOW)

    with pytest.raises(RuntimeError, match="bug"):
        await service.collect()
