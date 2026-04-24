from fastapi import APIRouter, HTTPException, status

from app.core.security.auth import CurrentUserId
from app.repositories.conversation_repository import ConversationRepository

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/{conversation_id}/history")
async def get_conversation_history(
    conversation_id: str,
    user_id: str = CurrentUserId,
):
    """Return all messages in a conversation ordered by created_at."""
    repo = ConversationRepository()

    if not repo.conversation_exists_for_user(conversation_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    messages = repo.get_conversation_messages(conversation_id)
    return {"conversation_id": conversation_id, "messages": messages}
