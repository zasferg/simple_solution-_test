import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from decimal import Decimal

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from app.domain.prices.exceptions import PriceFetchError
from app.domain.prices.types import Ticker
from app.infrastructure.deribit.client import DeribitClient, parse_index_price

SUCCESS_BODY = '{"jsonrpc":"2.0","result":{"estimated_delivery_price":83366.25,"index_price":83366.25}}'
ERROR_BODY = '{"jsonrpc":"2.0","error":{"code":-32602,"message":"Invalid params"}}'


@dataclass
class FakeDeribit:
    """Local HTTP server standing in for Deribit; the response is set per test."""

    base_url: str = ""
    status: int = 200
    body: str = SUCCESS_BODY
    delay_seconds: float = 0
    received_queries: list[dict[str, str]] = field(default_factory=list)

    async def handle(self, request: web.Request) -> web.Response:
        self.received_queries.append(dict(request.query))
        await asyncio.sleep(self.delay_seconds)
        return web.Response(status=self.status, text=self.body, content_type="application/json")


@pytest.fixture
async def deribit() -> AsyncIterator[FakeDeribit]:
    fake = FakeDeribit()
    app = web.Application()
    app.router.add_get("/api/v2/public/get_index_price", fake.handle)
    async with TestServer(app) as server:
        fake.base_url = str(server.make_url("/api/v2"))
        yield fake


@pytest.fixture
async def http_session() -> AsyncIterator[aiohttp.ClientSession]:
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=0.5)) as session:
        yield session


def test_parse_keeps_full_precision() -> None:
    body = '{"result":{"index_price":83366.123456789012345}}'

    assert parse_index_price(body) == Decimal("83366.123456789012345")


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(ERROR_BODY, id="json-rpc-error"),
        pytest.param("<html>Bad gateway</html>", id="not-json"),
        pytest.param('{"result":{}}', id="no-index-price"),
        pytest.param('{"result":{"index_price":"abc"}}', id="not-a-number"),
        pytest.param("[1, 2]", id="not-an-object"),
    ],
)
def test_parse_rejects_unexpected_body(body: str) -> None:
    with pytest.raises(PriceFetchError):
        parse_index_price(body)


async def test_fetch_requests_ticker_index_and_returns_price(
    deribit: FakeDeribit, http_session: aiohttp.ClientSession
) -> None:
    price = await DeribitClient(http_session, deribit.base_url).fetch_index_price(Ticker.ETH_USD)

    assert price == Decimal("83366.25")
    assert deribit.received_queries == [{"index_name": "eth_usd"}]


async def test_fetch_turns_api_error_into_fetch_error(
    deribit: FakeDeribit, http_session: aiohttp.ClientSession
) -> None:
    deribit.status, deribit.body = 400, ERROR_BODY

    with pytest.raises(PriceFetchError, match="Invalid params"):
        await DeribitClient(http_session, deribit.base_url).fetch_index_price(Ticker.BTC_USD)


async def test_fetch_turns_timeout_into_fetch_error(deribit: FakeDeribit, http_session: aiohttp.ClientSession) -> None:
    deribit.delay_seconds = 2

    with pytest.raises(PriceFetchError, match="request failed"):
        await DeribitClient(http_session, deribit.base_url).fetch_index_price(Ticker.BTC_USD)


async def test_fetch_turns_connection_error_into_fetch_error(http_session: aiohttp.ClientSession) -> None:
    unreachable = "http://127.0.0.1:1/api/v2"

    with pytest.raises(PriceFetchError, match="request failed"):
        await DeribitClient(http_session, unreachable).fetch_index_price(Ticker.BTC_USD)
