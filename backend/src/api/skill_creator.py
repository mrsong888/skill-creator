import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.agent.core import AgentCore
from src.config.settings import get_settings
from src.skill.manager import SkillManager
from src.workspace.manager import WorkspaceManager

router = APIRouter(prefix="/api/skill-creator", tags=["skill-creator"])

SKILL_CREATOR_PROMPT = """You are a skill creation assistant. Help the user create a new skill by:
1. Understanding their requirements
2. Generating a SKILL.md file with appropriate frontmatter and instructions
3. Suggesting test cases to validate the skill

A skill is defined by a SKILL.md file with YAML frontmatter (name, description, allowed-tools) and markdown content that serves as instructions for the AI agent when the skill is active."""


class StartRequest(BaseModel):
    message: str
    thread_id: str | None = None


class InstallRequest(BaseModel):
    thread_id: str
    skill_name: str


@router.post("/start")
async def start_creation(req: StartRequest):
    settings = get_settings()
    agent = AgentCore(model=settings.llm.model, api_key=settings.llm.api_key, base_url=settings.llm.base_url)

    async def event_generator():
        async for event in agent.run(
            [{"role": "user", "content": req.message}],
            system_prompt=SKILL_CREATOR_PROMPT,
        ):
            yield {"event": event["type"], "data": json.dumps(event["data"])}

    return EventSourceResponse(event_generator())


@router.post("/install")
async def install_from_draft(req: InstallRequest):
    settings = get_settings()
    wm = WorkspaceManager(base_path=settings.workspace.base_path)
    draft_dir = wm.get_thread_dir(req.thread_id) / "workspace" / "skill-draft" / req.skill_name

    if not (draft_dir / "SKILL.md").exists():
        raise HTTPException(status_code=404, detail="Skill draft not found")

    mgr = SkillManager(public_path=settings.skills.public_path, custom_path=settings.skills.custom_path)
    skill = mgr.install_skill(draft_dir)
    if not skill:
        raise HTTPException(status_code=400, detail="Failed to install skill")

    return {"name": skill.name, "installed": True}
