from app.repositories.message_repository import MessageRepository
from app.schemas.transcript import TranscriptResponse, UpdateTranscriptRequest


class TranscriptController:
    def __init__(self) -> None:
        self.message_repository = MessageRepository()

    async def update_transcript(
        self,
        transcript_id: str,
        payload: UpdateTranscriptRequest,
    ) -> TranscriptResponse:
        self.message_repository.update_transcript(transcript_id, payload.edited_text)
        return TranscriptResponse(
            transcript_id=transcript_id,
            edited_text=payload.edited_text,
        )
