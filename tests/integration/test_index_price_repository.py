from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.prices.schemas import IndexPrice
from app.domain.prices.types import Ticker
from app.infrastructure.database.repositories.index_price_repository import IndexPriceRepository
from app.infrastructure.database.tables import IndexPriceRecord


def make_price(timestamp: int, price: str = "1", ticker: Ticker = Ticker.BTC_USD) -> IndexPrice:
    return IndexPrice(ticker=ticker, price=Decimal(price), timestamp=timestamp)


async def test_add_many_skips_duplicates(db_session: AsyncSession) -> None:
    repository = IndexPriceRepository(db_session)

    await repository.add_many([make_price(10, "1.5"), make_price(10, "1.5", Ticker.ETH_USD)])
    await repository.add_many([make_price(10, "999")])

    assert await db_session.scalar(select(func.count()).select_from(IndexPriceRecord)) == 2
    assert await repository.get_latest(Ticker.BTC_USD) == make_price(10, "1.5")


async def test_price_keeps_decimal_precision(db_session: AsyncSession) -> None:
    repository = IndexPriceRepository(db_session)

    await repository.add_many([make_price(10, "83366.12345678")])

    latest = await repository.get_latest(Ticker.BTC_USD)
    assert latest is not None
    assert latest.price == Decimal("83366.12345678")


async def test_get_latest_is_per_ticker(db_session: AsyncSession) -> None:
    repository = IndexPriceRepository(db_session)
    await repository.add_many([make_price(10), make_price(30), make_price(20), make_price(99, ticker=Ticker.ETH_USD)])

    assert await repository.get_latest(Ticker.BTC_USD) == make_price(30)
    assert await repository.get_latest(Ticker.ETH_USD) == make_price(99, ticker=Ticker.ETH_USD)


async def test_get_latest_without_data(db_session: AsyncSession) -> None:
    assert await IndexPriceRepository(db_session).get_latest(Ticker.BTC_USD) is None


async def test_find_filters_range_inclusively_and_paginates(db_session: AsyncSession) -> None:
    repository = IndexPriceRepository(db_session)
    await repository.add_many([make_price(timestamp) for timestamp in (50, 10, 30, 20, 40)])

    in_range = await repository.find(Ticker.BTC_USD, limit=10, offset=0, date_from=20, date_to=40)
    page = await repository.find(Ticker.BTC_USD, limit=2, offset=1)

    assert [price.timestamp for price in in_range] == [20, 30, 40]
    assert [price.timestamp for price in page] == [20, 30]
