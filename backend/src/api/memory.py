from fastapi import APIRouter
from pydantic import BaseModel

from src.config.settings import get_settings
from src.memory.store import MemoryStore

router = APIRouter(prefix="/api/memory", tags=["memory"])


def get_memory_store() -> MemoryStore:
    settings = get_settings()
    return MemoryStore(storage_path=settings.memory.storage_path)


@router.get("")
async def get_memory():
    store = get_memory_store()
    return store.load()


@router.post("/reload")
async def reload_memory():
    store = get_memory_store()
    store.invalidate_cache()
    return store.load()


class MemoryUpdateRequest(BaseModel):
    context: dict | None = None
    facts: list[dict] | None = None


@router.put("")
async def update_memory(req: MemoryUpdateRequest):
    store = get_memory_store()
    data = store.load()
    if req.context:
        for key, value in req.context.items():
            if key in data["context"]:
                data["context"][key] = value
    if req.facts is not None:
        data["facts"] = req.facts
    store.save(data)
    return data
