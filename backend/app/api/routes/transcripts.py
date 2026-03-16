from fastapi import APIRouter

from app.api.controllers.transcript_controller import TranscriptController
from app.schemas.transcript import UpdateTranscriptRequest


router = APIRouter(prefix="/transcripts", tags=["transcripts"])
controller = TranscriptController()


@router.patch("/{transcript_id}")
async def update_transcript(
    transcript_id: str,
    payload: UpdateTranscriptRequest,
):
    return await controller.update_transcript(transcript_id, payload)
