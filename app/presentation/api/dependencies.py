from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.prices.services import PriceQueryService
from app.infrastructure.database.repositories.index_price_repository import IndexPriceRepository


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


def get_price_query_service(session: Annotated[AsyncSession, Depends(get_session)]) -> PriceQueryService:
    return PriceQueryService(IndexPriceRepository(session))


PriceQueryServiceDep = Annotated[PriceQueryService, Depends(get_price_query_service)]
