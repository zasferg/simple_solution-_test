from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.domain.prices.types import Ticker


class IndexPrice(BaseModel):
    """Index price of a ticker at a UNIX timestamp (seconds, UTC)."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    ticker: Ticker
    price: Decimal
    timestamp: int
