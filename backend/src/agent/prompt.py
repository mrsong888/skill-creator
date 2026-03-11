BASE_SYSTEM_PROMPT = """You are a helpful AI assistant integrated into a Chrome extension. You assist employees with their daily tasks, answer questions, and execute skills when bound to a conversation.

You have access to tools for file operations and other tasks. Use them when appropriate.

Be concise, accurate, and helpful. When a skill is active, follow its instructions precisely."""


def build_system_prompt(
    memory_text: str | None = None,
    skill_content: str | None = None,
    page_context: str | None = None,
) -> str:
    parts = [BASE_SYSTEM_PROMPT]

    if memory_text:
        parts.append(f"<memory>\n{memory_text}\n</memory>")

    if skill_content:
        parts.append(f"<skill>\n{skill_content}\n</skill>")

    if page_context:
        parts.append(f"<page_context>\n{page_context}\n</page_context>")

    return "\n\n".join(parts)
