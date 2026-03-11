import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _empty_memory() -> dict:
    return {
        "version": "1.0",
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "context": {
            "workContext": {"summary": "", "updatedAt": ""},
            "personalContext": {"summary": "", "updatedAt": ""},
            "topOfMind": {"summary": "", "updatedAt": ""},
        },
        "facts": [],
    }


class MemoryStore:
    def __init__(self, storage_path: str | Path = "data/memory.json"):
        self.storage_path = Path(storage_path)
        self._cache: dict | None = None

    def load(self) -> dict:
        if self._cache is not None:
            return self._cache
        if not self.storage_path.exists():
            self._cache = _empty_memory()
            return self._cache
        with open(self.storage_path) as f:
            self._cache = json.load(f)
        return self._cache

    def save(self, data: dict) -> None:
        data["lastUpdated"] = datetime.now(timezone.utc).isoformat()
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: write to temp file then rename
        fd, tmp_path = tempfile.mkstemp(dir=self.storage_path.parent, suffix=".tmp")
        try:
            with open(fd, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            Path(tmp_path).replace(self.storage_path)
        except Exception:
            Path(tmp_path).unlink(missing_ok=True)
            raise
        self._cache = data

    def invalidate_cache(self) -> None:
        self._cache = None
