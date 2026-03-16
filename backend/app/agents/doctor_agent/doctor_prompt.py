from app.core.config.prompt_loader import load_prompt_config


def build_doctor_system_prompt() -> str:
    prompt_config = load_prompt_config()
    base_prompt = prompt_config["doctor_system_prompt"]
    sections = ", ".join(prompt_config["response_sections"])
    return (
        f"{base_prompt}\n"
        f"Return JSON with the following sections: {sections}.\n"
        "Each list section should be concise, specific, and user-safe."
    )
