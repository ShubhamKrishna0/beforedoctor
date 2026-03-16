from fastapi import UploadFile

from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.audio import AudioTranscriptionResponse
from app.services.audio_service.audio_service import AudioService
from app.services.transcription_service.transcription_service import TranscriptionService


class AudioController:
    def __init__(self) -> None:
        self.conversation_repository = ConversationRepository()
        self.message_repository = MessageRepository()
        self.audio_service = AudioService()
        self.transcription_service = TranscriptionService()

    async def transcribe_audio(
        self,
        user_id: str,
        audio_file: UploadFile,
        conversation_id: str | None = None,
    ) -> AudioTranscriptionResponse:
        active_conversation_id = (
            conversation_id
            if conversation_id
            else self.conversation_repository.create_conversation(user_id)
        )

        audio_url = await self.audio_service.upload_user_audio(user_id, audio_file)
        await audio_file.seek(0)
        transcript_text = await self.transcription_service.transcribe(audio_file)
        message_id = self.message_repository.create_message(
            conversation_id=active_conversation_id,
            role="user",
            text=transcript_text,
            audio_url=audio_url,
        )
        transcript_id = self.message_repository.create_transcript(
            message_id=message_id,
            original_text=transcript_text,
            edited_text=transcript_text,
        )
        self.message_repository.create_audio_file(user_id=user_id, audio_url=audio_url)
        return AudioTranscriptionResponse(
            message_id=message_id,
            transcript_id=transcript_id,
            audio_url=audio_url,
            original_text=transcript_text,
            edited_text=transcript_text,
        )
