import json
import uuid
from datetime import datetime, timezone

import litellm

from src.memory.prompt import MEMORY_UPDATE_SYSTEM_PROMPT, build_memory_update_prompt
from src.memory.store import MemoryStore


def parse_memory_update_response(response_text: str) -> dict:
    """Parse LLM response into structured memory update."""
    try:
        text = response_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)
    except (json.JSONDecodeError, IndexError):
        return {"context_updates": {}, "new_facts": [], "remove_fact_ids": []}


def apply_memory_update(memory: dict, update: dict) -> dict:
    """Apply parsed update to memory data."""
    now = datetime.now(timezone.utc).isoformat()

    for key, summary in update.get("context_updates", {}).items():
        if key in memory.get("context", {}):
            memory["context"][key] = {"summary": summary, "updatedAt": now}

    remove_ids = set(update.get("remove_fact_ids", []))
    if remove_ids:
        memory["facts"] = [f for f in memory.get("facts", []) if f["id"] not in remove_ids]

    for fact in update.get("new_facts", []):
        memory["facts"].append({
            "id": f"fact_{uuid.uuid4().hex[:8]}",
            "content": fact["content"],
            "category": fact.get("category", "knowledge"),
            "confidence": fact.get("confidence", 0.8),
            "createdAt": now,
            "source": fact.get("source", ""),
        })

    return memory


async def run_memory_update(
    conversation: list[dict],
    store: MemoryStore,
    model: str = "gpt-4o",
    api_key: str = "",
    base_url: str = "",
) -> None:
    """Run LLM-driven memory update from a conversation."""
    memory = store.load()
    prompt = build_memory_update_prompt(conversation, memory)

    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": MEMORY_UPDATE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["api_base"] = base_url
    response = await litellm.acompletion(**kwargs)

    update = parse_memory_update_response(response.choices[0].message.content)
    memory = apply_memory_update(memory, update)
    store.save(memory)
