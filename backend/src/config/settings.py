import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


def _resolve_env_vars(value):
    """Resolve values starting with $ as environment variables."""
    if isinstance(value, str) and value.startswith("$"):
        return os.environ.get(value[1:], value)
    if isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_vars(v) for v in value]
    return value


@dataclass
class LLMConfig:
    model: str = "gpt-4o"
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class MemoryConfig:
    enabled: bool = True
    debounce_seconds: int = 30
    max_facts: int = 100
    fact_confidence_threshold: float = 0.7
    max_injection_tokens: int = 2000
    storage_path: str = "data/memory.json"


@dataclass
class SkillsConfig:
    public_path: str = "skills/public"
    custom_path: str = "skills/custom"


@dataclass
class DatabaseConfig:
    url: str = "sqlite+aiosqlite:///data/app.db"


@dataclass
class WorkspaceConfig:
    base_path: str = "data/threads"


@dataclass
class AppSettings:
    llm: LLMConfig = field(default_factory=LLMConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)


def load_settings(config_path: str | None = None) -> AppSettings:
    """Load settings from a YAML config file."""
    if config_path is None:
        for candidate in ["config.yaml", "../config.yaml"]:
            if Path(candidate).exists():
                config_path = candidate
                break

    raw = {}
    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}

    raw = _resolve_env_vars(raw)

    llm_data = raw.get("llm", {})
    memory_data = raw.get("memory", {})
    skills_data = raw.get("skills", {})
    database_data = raw.get("database", {})
    workspace_data = raw.get("workspace", {})

    return AppSettings(
        llm=LLMConfig(**{k: v for k, v in llm_data.items() if k in LLMConfig.__dataclass_fields__}),
        memory=MemoryConfig(**{k: v for k, v in memory_data.items() if k in MemoryConfig.__dataclass_fields__}),
        skills=SkillsConfig(**{k: v for k, v in skills_data.items() if k in SkillsConfig.__dataclass_fields__}),
        database=DatabaseConfig(**{k: v for k, v in database_data.items() if k in DatabaseConfig.__dataclass_fields__}),
        workspace=WorkspaceConfig(**{k: v for k, v in workspace_data.items() if k in WorkspaceConfig.__dataclass_fields__}),
    )


# Singleton
_settings: AppSettings | None = None


def get_settings(config_path: str | None = None) -> AppSettings:
    global _settings
    if _settings is None:
        _settings = load_settings(config_path)
    return _settings


def reset_settings() -> None:
    global _settings
    _settings = None
