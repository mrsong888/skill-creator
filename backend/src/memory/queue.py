import asyncio
import logging
from collections import defaultdict

from src.memory.store import MemoryStore
from src.memory.updater import run_memory_update

logger = logging.getLogger(__name__)


class MemoryUpdateQueue:
    def __init__(self, store: MemoryStore, debounce_seconds: float = 30.0, model: str = "gpt-4o"):
        self.store = store
        self.debounce_seconds = debounce_seconds
        self.model = model
        self._pending: dict[str, list[dict]] = defaultdict(list)
        self._timers: dict[str, asyncio.Task] = {}

    def enqueue(self, thread_id: str, messages: list[dict]) -> None:
        """Queue conversation messages for memory update (debounced per thread)."""
        self._pending[thread_id].extend(messages)

        if thread_id in self._timers:
            self._timers[thread_id].cancel()

        self._timers[thread_id] = asyncio.create_task(self._debounced_update(thread_id))

    async def _debounced_update(self, thread_id: str) -> None:
        await asyncio.sleep(self.debounce_seconds)
        messages = self._pending.pop(thread_id, [])
        self._timers.pop(thread_id, None)
        if not messages:
            return
        try:
            await run_memory_update(messages, self.store, model=self.model)
        except Exception:
            logger.exception(f"Memory update failed for thread {thread_id}")
