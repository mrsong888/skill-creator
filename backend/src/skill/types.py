from dataclasses import dataclass, field


@dataclass
class Skill:
    name: str
    description: str = ""
    license: str = ""
    allowed_tools: list[str] = field(default_factory=list)
    content: str = ""
    path: str = ""
    category: str = "custom"
    enabled: bool = True
