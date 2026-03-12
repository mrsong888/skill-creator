import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.config.settings import get_settings
from src.skill.evaluator import evaluate_skill_quality
from src.skill.manager import SkillManager
from src.skill.runtime_config import save_skill_config
from src.skill.template_manager import TemplateManager
from src.skill.validator import validate_skill_md

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/skill-templates", tags=["skill-templates"])


def _get_template_manager() -> TemplateManager:
    settings = get_settings()
    return TemplateManager(settings.skills.templates_path)


def _get_skill_manager() -> SkillManager:
    settings = get_settings()
    return SkillManager(public_path=settings.skills.public_path, custom_path=settings.skills.custom_path)


# --- Request/Response Models ---


class RenderRequest(BaseModel):
    variables: dict = Field(default_factory=dict)


class RenderResponse(BaseModel):
    content: str
    is_valid: bool
    validation_message: str


class CreateRequest(BaseModel):
    variables: dict = Field(default_factory=dict)
    skill_name: str | None = None
    content: str | None = None  # LLM-enhanced SKILL.md content from preview


class CreateResponse(BaseModel):
    success: bool
    skill_name: str
    message: str
    content: str


class ValidateRequest(BaseModel):
    content: str


class ValidateResponse(BaseModel):
    is_valid: bool
    message: str


class EvaluateRequest(BaseModel):
    content: str


# --- Endpoints ---


@router.get("")
async def list_templates():
    mgr = _get_template_manager()
    templates = mgr.list_templates()
    return [
        {
            "name": t.name,
            "description": t.description,
            "category": t.category,
            "version": t.version,
            "llm_enhance": t.llm_enhance,
            "variables": [
                {
                    "name": v.name,
                    "type": v.type,
                    "required": v.required,
                    "default": v.default,
                    "description": v.description,
                    "options": v.options,
                }
                for v in t.variables
            ],
        }
        for t in templates
    ]


@router.get("/{name}")
async def get_template(name: str):
    mgr = _get_template_manager()
    t = mgr.get_template(name)
    if t is None:
        raise HTTPException(status_code=404, detail=f"Template '{name}' not found")
    return {
        "name": t.name,
        "description": t.description,
        "category": t.category,
        "version": t.version,
        "llm_enhance": t.llm_enhance,
        "variables": [
            {
                "name": v.name,
                "type": v.type,
                "required": v.required,
                "default": v.default,
                "description": v.description,
                "options": v.options,
            }
            for v in t.variables
        ],
    }


@router.post("/{name}/render")
async def render_template(name: str, req: RenderRequest):
    mgr = _get_template_manager()
    template = mgr.get_template(name)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Template '{name}' not found")

    if not template.llm_enhance:
        try:
            content = mgr.render(name, req.variables)
            is_valid, msg = validate_skill_md(content)
            return RenderResponse(content=content, is_valid=is_valid, validation_message=msg)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        settings = get_settings()

        async def event_generator():
            async for event in mgr.render_with_llm(
                name,
                req.variables,
                model=settings.llm.model,
                api_key=settings.llm.api_key,
                base_url=settings.llm.base_url,
            ):
                yield {"event": event["type"], "data": json.dumps(event)}

        return EventSourceResponse(event_generator())


@router.post("/{name}/create")
async def create_from_template(name: str, req: CreateRequest):
    mgr = _get_template_manager()
    template = mgr.get_template(name)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Template '{name}' not found")

    # Use LLM-enhanced content from preview if provided, otherwise render from template
    if req.content:
        content = req.content
    else:
        try:
            content = mgr.render(name, req.variables)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    is_valid, msg = validate_skill_md(content)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Validation failed: {msg}")

    # Extract skill name from rendered frontmatter
    import re

    import yaml

    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if fm_match:
        fm = yaml.safe_load(fm_match.group(1))
        skill_name = req.skill_name or fm.get("name", name)
    else:
        skill_name = req.skill_name or name

    # Write to custom skills dir
    skill_mgr = _get_skill_manager()
    from pathlib import Path

    skill_dir = Path(skill_mgr.custom_path) / skill_name
    if skill_dir.exists():
        raise HTTPException(status_code=409, detail=f"Skill '{skill_name}' already exists")

    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

    # Write extra files (e.g. reference/*.md) if defined in the template
    try:
        extra_files = mgr.render_files(name, req.variables)
        for rel_path, file_content in extra_files.items():
            file_path = skill_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file_content, encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to write extra template files: {e}")

    # Build config.json with template metadata + optional runtime config
    skill_config: dict = {}

    # Record template metadata so the editing chat can enforce directory structure
    template_files = ["SKILL.md"] + sorted(extra_files.keys()) if extra_files else ["SKILL.md"]
    skill_config["_template"] = {
        "name": name,
        "version": template.version,
        "files": template_files,
    }

    # For sql-assistant template, save runtime config (connection info)
    if name == "sql-assistant":
        skill_config.update({
            "engine": req.variables.get("engine", "").lower(),
            "host": req.variables.get("host", ""),
            "port": int(req.variables.get("port", 0)),
            "username": req.variables.get("db_user", "default"),
            "password": req.variables.get("db_password", ""),
            "database": req.variables.get("database", ""),
        })

    save_skill_config(skill_dir, skill_config)

    logger.info(f"Skill '{skill_name}' created from template '{name}'")
    return CreateResponse(
        success=True,
        skill_name=skill_name,
        message=f"Skill '{skill_name}' created successfully",
        content=content,
    )


@router.post("/validate")
async def validate_content(req: ValidateRequest):
    is_valid, message = validate_skill_md(req.content)
    return ValidateResponse(is_valid=is_valid, message=message)


@router.post("/evaluate")
async def evaluate_content(req: EvaluateRequest):
    settings = get_settings()
    try:
        result = await evaluate_skill_quality(
            req.content,
            model=settings.llm.model,
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
