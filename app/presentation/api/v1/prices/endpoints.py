from typing import Annotated

from fastapi import APIRouter, Query

from app.domain.prices.schemas import IndexPrice
from app.domain.prices.types import Ticker
from app.presentation.api.dependencies import PriceQueryServiceDep

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000

Limit = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]
Offset = Annotated[int, Query(ge=0)]
UnixTime = Annotated[int, Query(ge=0, description="UNIX timestamp, seconds, UTC")]

router = APIRouter(prefix="/prices", tags=["Prices"])


@router.get("")
async def list_prices(
    ticker: Ticker,
    service: PriceQueryServiceDep,
    limit: Limit = DEFAULT_PAGE_SIZE,
    offset: Offset = 0,
) -> list[IndexPrice]:
    """All stored prices of the ticker, oldest first."""
    return await service.find(ticker, limit=limit, offset=offset)


@router.get("/latest")
async def get_latest_price(ticker: Ticker, service: PriceQueryServiceDep) -> IndexPrice:
    """The most recent stored price of the ticker."""
    return await service.get_latest(ticker)


@router.get("/range")
async def list_prices_in_range(
    ticker: Ticker,
    date_from: UnixTime,
    date_to: UnixTime,
    service: PriceQueryServiceDep,
    limit: Limit = DEFAULT_PAGE_SIZE,
    offset: Offset = 0,
) -> list[IndexPrice]:
    """Prices of the ticker with `date_from <= timestamp <= date_to`, oldest first."""
    return await service.find(ticker, limit=limit, offset=offset, date_from=date_from, date_to=date_to)
