from uuid import uuid4

from app.database.supabase_client import get_supabase_client


class ConversationRepository:
    def __init__(self) -> None:
        self.client = get_supabase_client()
        self.schema = "before_doctor"

    def ensure_user_exists(self, user_id: str) -> None:
        self.client.schema(self.schema).table("users").upsert(
            {"id": user_id, "email": f"{user_id}@dev.local"}
        ).execute()

    def create_conversation(self, user_id: str) -> str:
        self.ensure_user_exists(user_id)
        conversation_id = str(uuid4())
        self.client.schema(self.schema).table("conversations").insert(
            {"id": conversation_id, "user_id": user_id}
        ).execute()
        return conversation_id

    def get_conversation_messages(self, conversation_id: str) -> list[dict]:
        response = (
            self.client.schema(self.schema)
            .table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at")
            .execute()
        )
        return response.data or []
