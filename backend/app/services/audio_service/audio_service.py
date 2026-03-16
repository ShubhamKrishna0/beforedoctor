from datetime import datetime
from uuid import uuid4

from fastapi import UploadFile

from app.core.config.settings import get_settings
from app.database.supabase_client import get_supabase_client


class AudioService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = get_supabase_client()

    async def upload_user_audio(self, user_id: str, audio_file: UploadFile) -> str:
        file_ext = (audio_file.filename or "recording.wav").split(".")[-1]
        storage_path = f"{user_id}/{datetime.utcnow().isoformat()}-{uuid4()}.{file_ext}"
        payload = await audio_file.read()
        self.client.storage.from_(self.settings.supabase_storage_bucket).upload(
            storage_path,
            payload,
            {"content-type": audio_file.content_type or "audio/wav"},
        )
        return self.client.storage.from_(self.settings.supabase_storage_bucket).get_public_url(
            storage_path
        )

    def upload_generated_audio(self, user_id: str, audio_bytes: bytes) -> str:
        storage_path = f"{user_id}/responses/{datetime.utcnow().isoformat()}-{uuid4()}.mp3"
        self.client.storage.from_(self.settings.supabase_storage_bucket).upload(
            storage_path,
            audio_bytes,
            {"content-type": "audio/mpeg"},
        )
        return self.client.storage.from_(self.settings.supabase_storage_bucket).get_public_url(
            storage_path
        )
