from fastapi import UploadFile

from app.core.config.settings import get_settings
from app.services.ai_service.openai_client import get_openai_client


class TranscriptionService:
    async def transcribe(self, audio_file: UploadFile) -> str:
        settings = get_settings()
        client = get_openai_client()

        transcript = await client.audio.transcriptions.create(
            model=settings.openai_transcribe_model,
            file=(audio_file.filename or "audio.wav", await audio_file.read()),
        )
        return transcript.text
