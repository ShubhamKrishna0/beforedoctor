from openai import AsyncOpenAI

from app.core.config.settings import get_settings


def get_openai_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        project=settings.openai_project_id,
    )
