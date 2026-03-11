def format_memory_for_injection(
    memory: dict,
    max_facts: int = 15,
    min_confidence: float = 0.7,
) -> str:
    parts = []

    # Context sections
    context = memory.get("context", {})
    for key, label in [
        ("workContext", "Work Context"),
        ("personalContext", "Personal Context"),
        ("topOfMind", "Top of Mind"),
    ]:
        summary = context.get(key, {}).get("summary", "")
        if summary:
            parts.append(f"**{label}:** {summary}")

    # Facts (filtered by confidence, limited by max_facts)
    facts = memory.get("facts", [])
    filtered = sorted(
        [f for f in facts if f.get("confidence", 0) >= min_confidence],
        key=lambda f: f.get("confidence", 0),
        reverse=True,
    )[:max_facts]

    if filtered:
        fact_lines = [f"- [{f['category']}] {f['content']}" for f in filtered]
        parts.append("**Known Facts:**\n" + "\n".join(fact_lines))

    return "\n\n".join(parts)
