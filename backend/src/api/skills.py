from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config.settings import get_settings
from src.skill.manager import SkillManager

router = APIRouter(prefix="/api/skills", tags=["skills"])


def get_skill_manager() -> SkillManager:
    settings = get_settings()
    return SkillManager(
        public_path=settings.skills.public_path,
        custom_path=settings.skills.custom_path,
    )


@router.get("")
async def list_skills():
    mgr = get_skill_manager()
    skills = mgr.list_skills()
    return [
        {
            "name": s.name,
            "description": s.description,
            "category": s.category,
            "enabled": s.enabled,
        }
        for s in skills
    ]


@router.get("/{name}")
async def get_skill(name: str):
    mgr = get_skill_manager()
    skill = mgr.get_skill(name)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {
        "name": skill.name,
        "description": skill.description,
        "license": skill.license,
        "allowed_tools": skill.allowed_tools,
        "content": skill.content,
        "category": skill.category,
        "enabled": skill.enabled,
    }


class EnableRequest(BaseModel):
    enabled: bool


@router.put("/{name}")
async def update_skill_enabled(name: str, req: EnableRequest):
    mgr = get_skill_manager()
    skill = mgr.get_skill(name)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    mgr.set_enabled(name, req.enabled)
    return {"name": name, "enabled": req.enabled}


@router.delete("/{name}")
async def uninstall_skill(name: str):
    mgr = get_skill_manager()
    if not mgr.uninstall_skill(name):
        raise HTTPException(status_code=400, detail="Cannot uninstall: skill not found or is a public skill")
    return {"deleted": name}
