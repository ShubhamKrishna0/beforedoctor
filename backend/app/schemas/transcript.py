from pydantic import BaseModel, Field


class UpdateTranscriptRequest(BaseModel):
    edited_text: str = Field(min_length=2, max_length=4000)


class TranscriptResponse(BaseModel):
    transcript_id: str
    edited_text: str
