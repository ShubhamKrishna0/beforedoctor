from pathlib import Path

import yaml

from app.core.config.settings import get_settings


def load_prompt_config() -> dict:
    settings = get_settings()
    prompt_path = settings.project_root / "config" / "ai_prompts.yaml"
    with prompt_path.open("r", encoding="utf-8") as prompt_file:
        return yaml.safe_load(prompt_file)
