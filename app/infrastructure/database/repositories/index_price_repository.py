from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.prices.schemas import IndexPrice
from app.domain.prices.types import Ticker
from app.infrastructure.database.tables import IndexPriceRecord


class IndexPriceRepository:
    """PostgreSQL storage; satisfies PriceRepository. Never commits: the caller owns the transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_many(self, prices: Sequence[IndexPrice]) -> None:
        """Insert prices; a row with an already stored (ticker, timestamp) is silently skipped."""
        if not prices:
            return
        statement = (
            insert(IndexPriceRecord)
            .values([price.model_dump() for price in prices])
            .on_conflict_do_nothing(index_elements=["ticker", "timestamp"])
        )
        await self._session.execute(statement)

    async def get_latest(self, ticker: Ticker) -> IndexPrice | None:
        statement = (
            select(IndexPriceRecord)
            .where(IndexPriceRecord.ticker == ticker)
            .order_by(IndexPriceRecord.timestamp.desc())
            .limit(1)
        )
        record = await self._session.scalar(statement)
        return IndexPrice.model_validate(record) if record else None

    async def find(
        self,
        ticker: Ticker,
        *,
        limit: int,
        offset: int,
        date_from: int | None = None,
        date_to: int | None = None,
    ) -> list[IndexPrice]:
        """Prices in ascending time order, so pages stay stable while new rows are appended."""
        statement = select(IndexPriceRecord).where(IndexPriceRecord.ticker == ticker)
        if date_from is not None:
            statement = statement.where(IndexPriceRecord.timestamp >= date_from)
        if date_to is not None:
            statement = statement.where(IndexPriceRecord.timestamp <= date_to)
        statement = statement.order_by(IndexPriceRecord.timestamp).limit(limit).offset(offset)
        return [IndexPrice.model_validate(record) for record in await self._session.scalars(statement)]
