from fastapi import FastAPI

from app.api.routes import audio, chat, conversations, feedback, health, transcripts, users
from app.core.config.settings import get_settings
from app.core.security.rate_limiter import limiter


settings = get_settings()

app = FastAPI(
    title="Before Doctor API",
    version="1.0.0",
    description="Production-grade AI doctor assistant backend.",
)
app.state.limiter = limiter

app.include_router(health.router)
app.include_router(audio.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(transcripts.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "environment": settings.app_env}
