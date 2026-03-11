MEMORY_UPDATE_SYSTEM_PROMPT = """You are a memory extraction system. Analyze the conversation and extract:

1. **Context updates** - Updates to the user's work context, personal context, or top-of-mind priorities.
2. **New facts** - Discrete facts about the user (preferences, knowledge, behaviors, goals).
3. **Facts to remove** - IDs of previously stored facts that are now outdated or contradicted.

Respond with a JSON object:
```json
{
  "context_updates": {
    "workContext": "optional updated summary",
    "personalContext": "optional updated summary",
    "topOfMind": "optional updated summary"
  },
  "new_facts": [
    {"content": "fact text", "category": "preference|knowledge|context|behavior|goal", "confidence": 0.0-1.0}
  ],
  "remove_fact_ids": ["fact_id_1"]
}
```

Only include fields that need updating. Omit unchanged fields from context_updates.
Confidence should reflect how certain you are about the fact (0.7+ to store).
"""


def build_memory_update_prompt(conversation: list[dict], existing_memory: dict) -> str:
    conv_text = "\n".join(f"[{m['role']}]: {m['content']}" for m in conversation)
    existing_facts = "\n".join(
        f"- [{f['id']}] [{f['category']}] {f['content']}" for f in existing_memory.get("facts", [])
    )
    return f"""## Existing Memory

### Context
- Work: {existing_memory.get('context', {}).get('workContext', {}).get('summary', '')}
- Personal: {existing_memory.get('context', {}).get('personalContext', {}).get('summary', '')}
- Top of Mind: {existing_memory.get('context', {}).get('topOfMind', {}).get('summary', '')}

### Known Facts
{existing_facts or '(none)'}

## Recent Conversation
{conv_text}

Extract memory updates from this conversation."""
