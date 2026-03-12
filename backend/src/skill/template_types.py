from dataclasses import dataclass, field
from typing import Any


@dataclass
class TemplateVariable:
    """A variable placeholder in a skill template."""

    name: str
    type: str = "string"  # "string" | "text" | "list"
    required: bool = True
    default: Any = None
    description: str = ""
    options: list[str] = field(default_factory=list)


@dataclass
class SkillTemplate:
    """A skill template with metadata, variables, and prompt content."""

    name: str
    description: str
    category: str
    version: str
    llm_enhance: bool
    variables: list[TemplateVariable]
    frontmatter: dict
    prompt: str
    llm_enhance_prompt: str = ""
    path: str = ""
    files: dict[str, str] = field(default_factory=dict)  # relative_path -> template content
