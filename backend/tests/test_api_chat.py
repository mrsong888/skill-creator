from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.db.database import get_session
from src.db.models import Base
from src.main import app


@pytest.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_session():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    yield
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
async def client(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_get_chat_history_empty(client):
    response = await client.get("/api/chat/history")
    assert response.status_code == 200
    assert response.json() == []


async def test_get_thread_messages_empty(client):
    response = await client.get("/api/chat/nonexistent-thread")
    assert response.status_code == 200
    assert response.json() == []


async def test_chat_stream(client):
    """POST /api/chat returns SSE stream."""
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = "Hello!"
    mock_response.choices[0].message.tool_calls = None
    mock_response.choices[0].finish_reason = "stop"

    with patch("litellm.acompletion", return_value=mock_response):
        response = await client.post("/api/chat", json={"message": "Hi"})
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
