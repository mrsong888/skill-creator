import json
import logging
import re
from collections.abc import AsyncGenerator
from pathlib import Path

import yaml

from src.skill.template_loader import scan_templates_directory
from src.skill.template_types import SkillTemplate

logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages skill templates: listing, retrieval, rendering, and LLM-enhanced generation."""

    def __init__(self, templates_dir: str | Path):
        self.templates_dir = Path(templates_dir)

    def list_templates(self) -> list[SkillTemplate]:
        return scan_templates_directory(self.templates_dir)

    def get_template(self, name: str) -> SkillTemplate | None:
        for t in self.list_templates():
            if t.name == name:
                return t
        return None

    def render(self, name: str, variables: dict) -> str:
        """Render a template with pure string substitution."""
        template = self.get_template(name)
        if template is None:
            raise ValueError(f"Template '{name}' not found")

        resolved = {}
        for var in template.variables:
            value = variables.get(var.name)
            if value is None or value == "":
                if var.required and var.default is None:
                    raise ValueError(f"Missing required variable '{var.name}'")
                value = var.default if var.default is not None else ""
            if var.type == "list" and isinstance(value, list):
                value = "\n".join(f"- {item}" for item in value)
            resolved[var.name] = str(value) if value is not None else ""

        frontmatter = {}
        for key, val in template.frontmatter.items():
            if isinstance(val, str):
                frontmatter[key] = _substitute(val, resolved)
            else:
                frontmatter[key] = val

        body = _substitute(template.prompt, resolved)
        return _build_skill_md(frontmatter, body)

    async def render_with_llm(
        self,
        name: str,
        variables: dict,
        model: str = "gpt-4o",
        api_key: str = "",
        base_url: str = "",
    ) -> AsyncGenerator[dict, None]:
        """Render with LLM enhancement, yielding SSE-style dicts."""
        template = self.get_template(name)
        if template is None:
            yield {"type": "error", "content": f"Template '{name}' not found"}
            return

        try:
            base_content = self.render(name, variables)
        except ValueError as e:
            yield {"type": "error", "content": str(e)}
            return

        if not template.llm_enhance:
            yield {"type": "complete", "content": base_content}
            return

        enhance_prompt = template.llm_enhance_prompt or "Enhance this skill definition to be more detailed."

        # Split base content into frontmatter and body
        # LLM only enhances the body; frontmatter is preserved exactly
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", base_content, re.DOTALL)
        if fm_match:
            frontmatter_block = fm_match.group(1)
            body_content = fm_match.group(2).strip()
        else:
            frontmatter_block = ""
            body_content = base_content

        llm_prompt = (
            "You are a skill template enhancer. You will be given the markdown body of a SKILL.md file "
            "(the part AFTER the YAML frontmatter). Enhance it according to the instructions.\n\n"
            "IMPORTANT:\n"
            "- Output ONLY the enhanced markdown body. Do NOT include YAML frontmatter (no --- markers).\n"
            "- Do NOT wrap output in code blocks.\n"
            "- Preserve the overall structure (headings, sections).\n\n"
            f"Markdown body:\n{body_content}\n\n"
            f"Enhancement instructions: {enhance_prompt}\n\n"
            f"Variable values: {json.dumps(variables, indent=2)}\n\n"
            "Generate the enhanced markdown body:"
        )

        try:
            import litellm

            kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": llm_prompt}],
                "stream": True,
            }
            if api_key:
                kwargs["api_key"] = api_key
            if base_url:
                kwargs["api_base"] = base_url

            # Emit the frontmatter first so the UI shows it immediately
            frontmatter_str = f"---\n{frontmatter_block}\n---\n\n"
            yield {"type": "start", "content": frontmatter_str}

            full_body = ""
            response = await litellm.acompletion(**kwargs)
            async for chunk in response:
                delta = chunk.choices[0].delta
                text = delta.content if delta.content else ""
                if text:
                    full_body += text
                    yield {"type": "chunk", "content": text}

            # Strip code block wrappers if LLM added them
            stripped = full_body.strip()
            if stripped.startswith("```") and stripped.endswith("```"):
                stripped = re.sub(r"^```\w*\n?", "", stripped)
                stripped = re.sub(r"\n?```$", "", stripped)
                full_body = stripped

            full_content = frontmatter_str + full_body.strip() + "\n"
            yield {"type": "complete", "content": full_content}

        except Exception as e:
            logger.error(f"LLM enhancement failed: {e}", exc_info=True)
            yield {"type": "fallback", "content": base_content, "error": str(e)}


def _substitute(template_str: str, variables: dict) -> str:
    def replacer(match: re.Match) -> str:
        key = match.group(1)
        return variables.get(key, match.group(0))

    return re.sub(r"\$\{(\w+)\}", replacer, template_str)


def _build_skill_md(frontmatter: dict, body: str) -> str:
    fm_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True).strip()
    return f"---\n{fm_str}\n---\n\n{body}\n"
