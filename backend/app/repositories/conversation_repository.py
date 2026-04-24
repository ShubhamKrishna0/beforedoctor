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

    def conversation_exists_for_user(self, conversation_id: str, user_id: str) -> bool:
        response = (
            self.client.schema(self.schema)
            .table("conversations")
            .select("id")
            .eq("id", conversation_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return bool(response.data)

    def get_conversation_phase(self, conversation_id: str) -> str:
        """Return the current phase for a conversation, defaulting to 'gathering'."""
        response = (
            self.client.schema(self.schema)
            .table("conversations")
            .select("phase")
            .eq("id", conversation_id)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if rows and rows[0].get("phase"):
            return rows[0]["phase"]
        return "gathering"

    def update_conversation_phase(self, conversation_id: str, phase: str) -> None:
        """Update the phase column on a conversation row."""
        (
            self.client.schema(self.schema)
            .table("conversations")
            .update({"phase": phase})
            .eq("id", conversation_id)
            .execute()
        )

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
