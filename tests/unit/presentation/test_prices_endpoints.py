from collections.abc import AsyncIterator
from decimal import Decimal

import httpx
import pytest

from app.core.config import Settings
from app.domain.prices.schemas import IndexPrice
from app.domain.prices.services import PriceQueryService
from app.domain.prices.types import Ticker
from app.infrastructure.application.factory import create_app
from app.presentation.api.dependencies import get_price_query_service
from tests.fakes import InMemoryPriceRepository


@pytest.fixture
def repository() -> InMemoryPriceRepository:
    return InMemoryPriceRepository(
        [
            IndexPrice(ticker=Ticker.BTC_USD, price=Decimal("100.5"), timestamp=10),
            IndexPrice(ticker=Ticker.BTC_USD, price=Decimal("200.25"), timestamp=20),
            IndexPrice(ticker=Ticker.BTC_USD, price=Decimal("300"), timestamp=30),
            IndexPrice(ticker=Ticker.ETH_USD, price=Decimal("5"), timestamp=20),
        ]
    )


@pytest.fixture
async def client(settings: Settings, repository: InMemoryPriceRepository) -> AsyncIterator[httpx.AsyncClient]:
    """The service is overridden, and ASGITransport does not run lifespan: no database is touched."""
    app = create_app(settings)
    app.dependency_overrides[get_price_query_service] = lambda: PriceQueryService(repository)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def test_list_returns_ticker_prices_oldest_first(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/prices", params={"ticker": "btc_usd"})

    assert response.status_code == 200
    assert [item["timestamp"] for item in response.json()] == [10, 20, 30]


async def test_list_is_paginated(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/prices", params={"ticker": "btc_usd", "limit": 1, "offset": 1})

    assert response.json() == [{"ticker": "btc_usd", "price": "200.25", "timestamp": 20}]


async def test_latest_returns_most_recent_price(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/prices/latest", params={"ticker": "btc_usd"})

    assert response.status_code == 200
    assert response.json() == {"ticker": "btc_usd", "price": "300", "timestamp": 30}


async def test_latest_without_data_returns_404(client: httpx.AsyncClient, repository: InMemoryPriceRepository) -> None:
    repository.prices.clear()

    response = await client.get("/v1/prices/latest", params={"ticker": "btc_usd"})

    assert response.status_code == 404
    assert response.json() == {"detail": "No prices stored for btc_usd"}


async def test_range_filters_by_timestamp_inclusively(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/prices/range", params={"ticker": "btc_usd", "date_from": 20, "date_to": 30})

    assert [item["timestamp"] for item in response.json()] == [20, 30]


async def test_range_rejects_reversed_dates(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/prices/range", params={"ticker": "btc_usd", "date_from": 30, "date_to": 20})

    assert response.status_code == 422
    assert response.json() == {"detail": "date_from must not be later than date_to"}


@pytest.mark.parametrize("path", ["/v1/prices", "/v1/prices/latest", "/v1/prices/range"])
async def test_ticker_is_required(client: httpx.AsyncClient, path: str) -> None:
    response = await client.get(path, params={"date_from": 0, "date_to": 1})

    assert response.status_code == 422


async def test_unknown_ticker_is_rejected(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/prices/latest", params={"ticker": "doge_usd"})

    assert response.status_code == 422


async def test_page_size_is_limited(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/prices", params={"ticker": "btc_usd", "limit": 1001})

    assert response.status_code == 422


async def test_health(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")

    assert response.json() == {"status": "ok"}
