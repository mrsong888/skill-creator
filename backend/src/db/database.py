from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import Base

_engine = None
_session_factory = None


async def init_db(database_url: str = "sqlite+aiosqlite:///data/app.db"):
    global _engine, _session_factory
    _engine = create_async_engine(database_url)
    _session_factory = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with _session_factory() as session:
        yield session


async def close_db():
    global _engine
    if _engine:
        await _engine.dispose()
