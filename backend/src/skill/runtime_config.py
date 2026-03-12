import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def save_skill_config(skill_path: Path, config: dict) -> None:
    """Save skill runtime configuration to skill_path/config.json."""
    config_file = Path(skill_path) / "config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Saved skill config to {config_file}")


def load_skill_config(skill_path: Path) -> dict | None:
    """Load skill runtime configuration from skill_path/config.json."""
    config_file = Path(skill_path) / "config.json"
    if not config_file.exists():
        return None
    try:
        return json.loads(config_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to load skill config from {config_file}: {e}")
        return None
