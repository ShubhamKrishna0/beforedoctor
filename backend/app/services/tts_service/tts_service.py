from app.core.config.settings import get_settings
from app.services.ai_service.openai_client import get_openai_client


class TTSService:
    async def synthesize(self, text: str) -> bytes:
        settings = get_settings()
        client = get_openai_client()

        response = await client.audio.speech.create(
            model=settings.openai_tts_model,
            voice=settings.openai_tts_voice,
            input=text,
            response_format="mp3",
        )
        return response.read()
