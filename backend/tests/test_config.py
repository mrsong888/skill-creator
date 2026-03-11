import os
import tempfile

import yaml

from src.config.settings import load_settings


def test_load_settings_from_yaml():
    config = {
        "llm": {"model": "gpt-4o", "api_key": "test-key"},
        "memory": {"enabled": True, "debounce_seconds": 30},
        "skills": {"public_path": "skills/public", "custom_path": "skills/custom"},
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config, f)
        f.flush()
        settings = load_settings(f.name)

    assert settings.llm.model == "gpt-4o"
    assert settings.llm.api_key == "test-key"
    assert settings.memory.enabled is True
    assert settings.memory.debounce_seconds == 30
    os.unlink(f.name)


def test_load_settings_defaults():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({}, f)
        f.flush()
        settings = load_settings(f.name)

    assert settings.llm.model == "gpt-4o"
    assert settings.memory.enabled is True
    os.unlink(f.name)


def test_env_var_resolution():
    os.environ["TEST_API_KEY"] = "resolved-key"
    config = {"llm": {"model": "gpt-4o", "api_key": "$TEST_API_KEY"}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config, f)
        f.flush()
        settings = load_settings(f.name)

    assert settings.llm.api_key == "resolved-key"
    os.unlink(f.name)
    del os.environ["TEST_API_KEY"]
