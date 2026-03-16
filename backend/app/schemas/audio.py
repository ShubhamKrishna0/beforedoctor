from pydantic import BaseModel, HttpUrl


class AudioTranscriptionResponse(BaseModel):
    message_id: str
    transcript_id: str
    audio_url: HttpUrl | str
    original_text: str
    edited_text: str
