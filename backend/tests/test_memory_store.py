import json

from src.memory.store import MemoryStore


def test_load_empty(temp_dir):
    store = MemoryStore(storage_path=temp_dir / "memory.json")
    data = store.load()
    assert data["version"] == "1.0"
    assert data["context"]["workContext"]["summary"] == ""
    assert data["facts"] == []


def test_save_and_load(temp_dir):
    path = temp_dir / "memory.json"
    store = MemoryStore(storage_path=path)
    data = store.load()
    data["context"]["workContext"]["summary"] = "Works on AI tools"
    data["facts"].append({
        "id": "fact_1",
        "content": "Prefers Python",
        "category": "preference",
        "confidence": 0.9,
        "createdAt": "2026-03-12T00:00:00Z",
        "source": "thread_1",
    })
    store.save(data)

    # Invalidate cache to force re-read from disk
    store.invalidate_cache()
    reloaded = store.load()
    assert reloaded["context"]["workContext"]["summary"] == "Works on AI tools"
    assert len(reloaded["facts"]) == 1
    assert reloaded["facts"][0]["content"] == "Prefers Python"


def test_atomic_save(temp_dir):
    path = temp_dir / "memory.json"
    store = MemoryStore(storage_path=path)
    data = store.load()
    data["facts"].append({
        "id": "fact_2",
        "content": "Uses VSCode",
        "category": "preference",
        "confidence": 0.8,
        "createdAt": "2026-03-12T00:00:00Z",
        "source": "thread_2",
    })
    store.save(data)
    assert path.exists()
    content = json.loads(path.read_text())
    assert len(content["facts"]) == 1
