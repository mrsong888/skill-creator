from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.memory.store import MemoryStore


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_get_memory(client, temp_dir):
    store = MemoryStore(storage_path=temp_dir / "memory.json")
    with patch("src.api.memory.get_memory_store", return_value=store):
        response = await client.get("/api/memory")
    assert response.status_code == 200
    data = response.json()
    assert "context" in data
    assert "facts" in data


async def test_reload_memory(client, temp_dir):
    store = MemoryStore(storage_path=temp_dir / "memory.json")
    with patch("src.api.memory.get_memory_store", return_value=store):
        response = await client.post("/api/memory/reload")
    assert response.status_code == 200
    assert "version" in response.json()


async def test_update_memory(client, temp_dir):
    store = MemoryStore(storage_path=temp_dir / "memory.json")
    with patch("src.api.memory.get_memory_store", return_value=store):
        response = await client.put("/api/memory", json={
            "context": {
                "workContext": {"summary": "Updated context", "updatedAt": "2026-03-12"}
            }
        })
    assert response.status_code == 200
    assert response.json()["context"]["workContext"]["summary"] == "Updated context"
