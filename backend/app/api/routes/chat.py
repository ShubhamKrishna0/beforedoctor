from fastapi import APIRouter

from app.api.controllers.chat_controller import ChatController
from app.core.security.auth import CurrentUserId
from app.schemas.chat import ChatMessageRequest


router = APIRouter(prefix="/chat", tags=["chat"])
controller = ChatController()


@router.post("/message")
async def send_message(
    payload: ChatMessageRequest,
    user_id: str = CurrentUserId,
):
    return await controller.send_message(user_id, payload)
