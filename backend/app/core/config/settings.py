from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Before Doctor"
    app_env: str = Field(default="development", alias="APP_ENV")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    openai_project_id: str | None = Field(
        default=None, alias="OPENAI_PROJECT_ID")
    openai_transcribe_model: str = Field(
        default="gpt-4o-transcribe",
        alias="OPENAI_TRANSCRIBE_MODEL",
    )
    openai_doctor_model: str = Field(
        default="gpt-4.1-mini", alias="OPENAI_DOCTOR_MODEL")
    openai_doctor_fallback_model: str = Field(
        default="gpt-4.1-mini",
        alias="OPENAI_DOCTOR_FALLBACK_MODEL",
    )
    openai_doctor_timeout_seconds: float = Field(
        default=25.0,
        alias="OPENAI_DOCTOR_TIMEOUT_SECONDS",
    )
    openai_tts_model: str = Field(
        default="gpt-4o-mini-tts", alias="OPENAI_TTS_MODEL")
    openai_tts_voice: str = Field(default="alloy", alias="OPENAI_TTS_VOICE")

    supabase_url: str = Field(alias="SUPABASE_URL")
    supabase_key: str = Field(alias="SUPABASE_KEY")
    supabase_jwt_secret: str | None = Field(
        default=None, alias="SUPABASE_JWT_SECRET")
    supabase_storage_bucket: str = Field(
        default="audio-files",
        alias="SUPABASE_STORAGE_BUCKET",
    )

    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    enable_tts: bool = Field(default=True, alias="ENABLE_TTS")
    tts_timeout_seconds: float = Field(default=8.0, alias="TTS_TIMEOUT_SECONDS")
    enable_background_queue: bool = Field(
        default=False, alias="ENABLE_BACKGROUND_QUEUE")
    redis_url: str = Field(
        default="redis://localhost:6379/0", alias="REDIS_URL")
    rate_limit_requests: int = Field(default=60, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(
        default=60, alias="RATE_LIMIT_WINDOW_SECONDS")

    project_root: Path = Path(__file__).resolve().parents[3]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
