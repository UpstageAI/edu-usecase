from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..storage import UploadStorage


def get_storage(request: Request) -> UploadStorage:
    return request.app.state.storage  # type: ignore[attr-defined]


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.db_sessionmaker  # type: ignore[attr-defined]
    async with session_factory() as session:
        yield session
