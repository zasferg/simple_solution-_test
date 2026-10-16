from app.domain.prices.types import Ticker
from app.infrastructure.errors.base import NotFoundError, UnprocessableError


class PriceFetchError(Exception):
    """The exchange did not return a usable price; handled by the collector, never reaches the API."""


class PriceNotFoundError(NotFoundError):
    def __init__(self, ticker: Ticker) -> None:
        super().__init__(f"No prices stored for {ticker}")


class InvalidDateRangeError(UnprocessableError):
    def __init__(self) -> None:
        super().__init__("date_from must not be later than date_to")
