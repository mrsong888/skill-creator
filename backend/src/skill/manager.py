import json
import shutil
from pathlib import Path

from src.skill.loader import parse_skill_md, scan_skills_directory
from src.skill.types import Skill


class SkillManager:
    def __init__(
        self,
        public_path: str | Path = "skills/public",
        custom_path: str | Path = "skills/custom",
        extensions_config_path: str | Path | None = None,
    ):
        self.public_path = Path(public_path)
        self.custom_path = Path(custom_path)
        self.extensions_config_path = Path(extensions_config_path) if extensions_config_path else None

    def _load_enabled_state(self) -> dict[str, bool]:
        if not self.extensions_config_path or not self.extensions_config_path.exists():
            return {}
        with open(self.extensions_config_path) as f:
            data = json.load(f)
        return {name: cfg.get("enabled", True) for name, cfg in data.get("skills", {}).items()}

    def _save_enabled_state(self, states: dict[str, bool]) -> None:
        if not self.extensions_config_path:
            return
        data = {}
        if self.extensions_config_path.exists():
            with open(self.extensions_config_path) as f:
                data = json.load(f)
        data.setdefault("skills", {})
        for name, enabled in states.items():
            data["skills"].setdefault(name, {})["enabled"] = enabled
        self.extensions_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.extensions_config_path, "w") as f:
            json.dump(data, f, indent=2)

    def list_skills(self) -> list[Skill]:
        enabled_states = self._load_enabled_state()
        skills = []
        for skill in scan_skills_directory(self.public_path, category="public"):
            skill.enabled = enabled_states.get(skill.name, True)
            skills.append(skill)
        for skill in scan_skills_directory(self.custom_path, category="custom"):
            skill.enabled = enabled_states.get(skill.name, True)
            skills.append(skill)
        return skills

    def get_skill(self, name: str) -> Skill | None:
        for skill in self.list_skills():
            if skill.name == name:
                return skill
        return None

    def set_enabled(self, name: str, enabled: bool) -> None:
        states = self._load_enabled_state()
        states[name] = enabled
        self._save_enabled_state(states)

    def install_skill(self, skill_dir: Path) -> Skill | None:
        """Install a skill from a directory into custom skills."""
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return None
        skill = parse_skill_md(skill_md)
        dest = self.custom_path / skill.name
        if dest.exists():
            shutil.rmtree(dest)
        self.custom_path.mkdir(parents=True, exist_ok=True)
        shutil.copytree(skill_dir, dest)
        skill.path = str(dest)
        skill.category = "custom"
        return skill

    def uninstall_skill(self, name: str) -> bool:
        """Uninstall a custom skill. Returns False if skill is public or not found."""
        skill = self.get_skill(name)
        if not skill or skill.category != "custom":
            return False
        shutil.rmtree(skill.path)
        return True
