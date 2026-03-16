from fastapi import APIRouter, File, Form, UploadFile

from app.api.controllers.audio_controller import AudioController
from app.core.security.auth import CurrentUserId


router = APIRouter(prefix="/audio", tags=["audio"])
controller = AudioController()


@router.post("/transcribe")
async def transcribe_audio(
    user_id: str = CurrentUserId,
    file: UploadFile = File(...),
    conversation_id: str | None = Form(default=None),
):
    return await controller.transcribe_audio(user_id, file, conversation_id)
