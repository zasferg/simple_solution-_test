import json
from decimal import Decimal

import aiohttp

from app.domain.prices.exceptions import PriceFetchError
from app.domain.prices.types import Ticker

INDEX_PRICE_PATH = "/public/get_index_price"
MAX_LOGGED_BODY_LENGTH = 200


def parse_index_price(body: str) -> Decimal:
    """
    Extract `result.index_price` from a Deribit JSON-RPC response body.

    Any other shape, including a JSON-RPC `error` object, is a PriceFetchError.
    Floats are parsed straight into Decimal so the price never passes through float.
    """
    try:
        payload = json.loads(body, parse_float=Decimal)
        return Decimal(payload["result"]["index_price"])
    except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
        raise PriceFetchError(f"Unexpected Deribit response: {body[:MAX_LOGGED_BODY_LENGTH]}") from exc


class DeribitClient:
    """Public Deribit REST API; satisfies PriceClient."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str) -> None:
        self._session = session
        self._url = f"{base_url.rstrip('/')}{INDEX_PRICE_PATH}"

    async def fetch_index_price(self, ticker: Ticker) -> Decimal:
        try:
            async with self._session.get(self._url, params={"index_name": ticker.value}) as response:
                body = await response.text()
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise PriceFetchError(f"Deribit request failed for {ticker}: {exc!r}") from exc
        return parse_index_price(body)
