from pathlib import Path
import yaml
from app.core.config.settings import get_settings


def load_prompt_config() -> dict:
    settings = get_settings()
    candidates = [
        settings.project_root / "config" / "ai_prompts.yaml",
        settings.project_root / "backend" / "config" / "ai_prompts.yaml",
        Path(__file__).resolve().parents[3] / "config" / "ai_prompts.yaml",
        Path(__file__).resolve().parents[2] / "config" / "ai_prompts.yaml",
    ]
    for prompt_path in candidates:
        if prompt_path.exists():
            with prompt_path.open("r", encoding="utf-8") as prompt_file:
                return yaml.safe_load(prompt_file)
    raise FileNotFoundError(
        "ai_prompts.yaml not found. Searched: "
        + ", ".join(str(path) for path in candidates)
    )
