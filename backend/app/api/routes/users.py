from fastapi import APIRouter, HTTPException, status

from app.core.security.auth import CurrentUserId
from app.services.memory.memory_layer import MemoryLayer

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}/medical-memory")
async def get_medical_memory(
    user_id: str,
    current_user_id: str = CurrentUserId,
):
    """Return all active medical facts for the user."""
    # Ensure the authenticated user can only access their own data
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    memory_layer = MemoryLayer()
    facts = await memory_layer.get_active_facts(user_id)
    return {
        "user_id": user_id,
        "facts": [fact.model_dump() for fact in facts],
    }
