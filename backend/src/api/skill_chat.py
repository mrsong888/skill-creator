"""Skill editing chat endpoint with SSE streaming.

Allows users to chat with an LLM that can read and modify skill .md files.
"""

import json
import re
from collections.abc import AsyncGenerator
from pathlib import Path

import litellm
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.config.settings import get_settings
from src.skill.manager import SkillManager
from src.skill.runtime_config import load_skill_config
from src.skill.validator import validate_skill_md

router = APIRouter(prefix="/api/skills", tags=["skills"])

SYSTEM_PROMPT_TEMPLATE = """You are a Skill editing assistant. The user will tell you problems or improvement suggestions for the skill.

Current skill files:
{file_blocks}

Rules:
1. First reply in natural language, explaining what you understand about the problem and what changes you plan to make.
2. For files that need modification, output the COMPLETE file content wrapped in <file path="relative_path"> tags.
3. Only output files that need changes — do not output unchanged files.
4. Do not change the 'name' field in SKILL.md frontmatter.
5. If the user is only asking a question without requesting changes, just reply with text.
6. Always preserve the YAML frontmatter format in SKILL.md (--- delimiters).
{structure_constraint}"""

STRUCTURE_CONSTRAINT_TEMPLATE = """7. IMPORTANT: This skill was created from a template. The directory structure is FIXED — you can ONLY modify the following files:
{allowed_files_list}
Do NOT create new files or rename existing files. Only modify content within the allowed files above.
"""

STRUCTURE_UNCONSTRAINED = "7. You may create new files under the reference/ directory if needed.\n"

FILE_TAG_PATTERN = re.compile(r"<file\s+path=[\"']([^\"']+)[\"']\s*>(.*?)</file>", re.DOTALL)

ALLOWED_EXTENSIONS = {".md"}


def get_template_allowed_files(skill_dir: Path) -> list[str] | None:
    """If the skill was created from a template, return the list of allowed files.

    Returns None if the skill has no template constraint (free-form editing allowed).
    """
    config = load_skill_config(skill_dir)
    if not config:
        return None
    template_meta = config.get("_template")
    if not template_meta or not isinstance(template_meta, dict):
        return None
    files = template_meta.get("files")
    if isinstance(files, list) and len(files) > 0:
        return files
    return None


class SkillChatMessage(BaseModel):
    role: str
    content: str


class SkillChatRequest(BaseModel):
    message: str
    history: list[SkillChatMessage] = Field(default_factory=list)


def _get_skill_manager() -> SkillManager:
    settings = get_settings()
    return SkillManager(
        public_path=settings.skills.public_path,
        custom_path=settings.skills.custom_path,
    )


def read_skill_md_files(skill_dir: Path) -> dict[str, str]:
    """Read all .md files from a skill directory."""
    files: dict[str, str] = {}
    for md_file in sorted(skill_dir.rglob("*.md")):
        rel_path = str(md_file.relative_to(skill_dir))
        try:
            files[rel_path] = md_file.read_text(encoding="utf-8")
        except Exception:
            pass
    return files


def build_file_blocks(files: dict[str, str]) -> str:
    """Build file content blocks for the system prompt."""
    blocks = []
    for path, content in sorted(files.items()):
        blocks.append(f'<file path="{path}">\n{content}\n</file>')
    return "\n\n".join(blocks)


def validate_file_path(rel_path: str, skill_dir: Path) -> Path | None:
    """Validate that a relative file path is safe and within the skill directory."""
    if not any(rel_path.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        return None
    if ".." in rel_path or rel_path.startswith("/"):
        return None
    target = (skill_dir / rel_path).resolve()
    try:
        target.relative_to(skill_dir.resolve())
    except ValueError:
        return None
    return target


def parse_file_updates(response_text: str) -> list[tuple[str, str]]:
    """Parse <file path="...">content</file> tags from the response."""
    return [(m.group(1), m.group(2).strip()) for m in FILE_TAG_PATTERN.finditer(response_text)]


@router.get("/{name}/files")
async def get_skill_files(name: str):
    """Get all .md files in a skill directory."""
    mgr = _get_skill_manager()
    skill = mgr.get_skill(name)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    files = read_skill_md_files(Path(skill.path))
    return {"files": files}


@router.post("/{name}/chat")
async def skill_chat(name: str, req: SkillChatRequest):
    """Chat endpoint for editing skills via LLM.

    Streams SSE events:
    - content_delta: Text chunk from the LLM response
    - file_updated: A file was successfully updated
    - file_skipped: A file update was skipped
    - error: An error occurred
    - message_end: End of response
    """
    mgr = _get_skill_manager()
    skill = mgr.get_skill(name)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    skill_dir = Path(skill.path)
    files = read_skill_md_files(skill_dir)

    async def event_generator() -> AsyncGenerator[dict, None]:
        settings = get_settings()
        file_blocks = build_file_blocks(files)

        # Determine template structure constraint
        allowed_files = get_template_allowed_files(skill_dir)
        if allowed_files is not None:
            allowed_files_list = "\n".join(f"   - {f}" for f in allowed_files)
            structure_constraint = STRUCTURE_CONSTRAINT_TEMPLATE.format(allowed_files_list=allowed_files_list)
        else:
            structure_constraint = STRUCTURE_UNCONSTRAINED

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(file_blocks=file_blocks, structure_constraint=structure_constraint)

        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        for msg in req.history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": req.message})

        kwargs: dict = {
            "model": settings.llm.model,
            "messages": messages,
            "temperature": settings.llm.temperature,
            "max_tokens": settings.llm.max_tokens,
        }
        if settings.llm.api_key:
            kwargs["api_key"] = settings.llm.api_key
        if settings.llm.base_url:
            kwargs["api_base"] = settings.llm.base_url

        full_response = ""
        kwargs["stream"] = True

        try:
            response = await litellm.acompletion(**kwargs)
            async for chunk in response:
                delta = chunk.choices[0].delta
                text = delta.content if delta.content else ""
                if text:
                    full_response += text
                    yield {"event": "content_delta", "data": json.dumps({"delta": text})}
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"message": str(e)})}
            yield {"event": "message_end", "data": json.dumps({"finish_reason": "error"})}
            return

        # Parse and write file updates
        file_updates = parse_file_updates(full_response)
        for rel_path, content in file_updates:
            # Enforce template directory structure constraint
            if allowed_files is not None and rel_path not in allowed_files:
                yield {
                    "event": "file_skipped",
                    "data": json.dumps({"path": rel_path, "reason": "Directory structure is locked by template — only existing files can be modified"}),
                }
                continue

            target = validate_file_path(rel_path, skill_dir)
            if target is None:
                yield {
                    "event": "file_skipped",
                    "data": json.dumps({"path": rel_path, "reason": "Invalid or disallowed path"}),
                }
                continue

            # Validate SKILL.md before writing
            if rel_path == "SKILL.md":
                is_valid, validation_msg = validate_skill_md(content)
                if not is_valid:
                    yield {
                        "event": "file_skipped",
                        "data": json.dumps({"path": rel_path, "reason": f"Invalid SKILL.md: {validation_msg}"}),
                    }
                    continue

            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                yield {
                    "event": "file_updated",
                    "data": json.dumps({"path": rel_path, "content": content}),
                }
            except Exception as e:
                yield {
                    "event": "file_skipped",
                    "data": json.dumps({"path": rel_path, "reason": str(e)}),
                }

        yield {"event": "message_end", "data": json.dumps({"finish_reason": "stop"})}

    return EventSourceResponse(event_generator())
