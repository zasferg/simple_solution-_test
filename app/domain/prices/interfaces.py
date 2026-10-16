from collections.abc import Sequence
from decimal import Decimal
from typing import Protocol

from app.domain.prices.schemas import IndexPrice
from app.domain.prices.types import Ticker


class PriceClient(Protocol):
    """Source of current index prices."""

    async def fetch_index_price(self, ticker: Ticker) -> Decimal: ...


class PriceRepository(Protocol):
    """Storage of collected index prices."""

    async def add_many(self, prices: Sequence[IndexPrice]) -> None: ...

    async def get_latest(self, ticker: Ticker) -> IndexPrice | None: ...

    async def find(
        self,
        ticker: Ticker,
        *,
        limit: int,
        offset: int,
        date_from: int | None = None,
        date_to: int | None = None,
    ) -> list[IndexPrice]: ...
