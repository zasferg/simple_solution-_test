from collections.abc import Sequence
from decimal import Decimal

from app.domain.prices.schemas import IndexPrice
from app.domain.prices.types import Ticker


class FakePriceClient:
    """PriceClient returning a fixed price or raising a fixed exception per ticker."""

    def __init__(self, outcomes: dict[Ticker, Decimal | Exception]) -> None:
        self._outcomes = outcomes

    async def fetch_index_price(self, ticker: Ticker) -> Decimal:
        outcome = self._outcomes[ticker]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class InMemoryPriceRepository:
    """PriceRepository over a list, with the same ordering and filtering as the SQL one."""

    def __init__(self, prices: Sequence[IndexPrice] = ()) -> None:
        self.prices = list(prices)

    async def add_many(self, prices: Sequence[IndexPrice]) -> None:
        self.prices.extend(prices)

    async def get_latest(self, ticker: Ticker) -> IndexPrice | None:
        own = [price for price in self.prices if price.ticker == ticker]
        return max(own, key=lambda price: price.timestamp, default=None)

    async def find(
        self,
        ticker: Ticker,
        *,
        limit: int,
        offset: int,
        date_from: int | None = None,
        date_to: int | None = None,
    ) -> list[IndexPrice]:
        own = sorted((price for price in self.prices if price.ticker == ticker), key=lambda price: price.timestamp)
        own = [
            price
            for price in own
            if (date_from is None or price.timestamp >= date_from) and (date_to is None or price.timestamp <= date_to)
        ]
        return own[offset : offset + limit]
