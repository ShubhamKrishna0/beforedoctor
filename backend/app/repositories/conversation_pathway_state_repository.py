import logging

from app.database.supabase_client import get_supabase_client
from app.models.pathway_models import PathwayState

logger = logging.getLogger(__name__)


class ConversationPathwayStateRepository:
    def __init__(self) -> None:
        self.client = get_supabase_client()
        self.schema = "before_doctor"

    def get_state(self, conversation_id: str) -> PathwayState | None:
        """Load pathway state for a conversation. Returns None if not found."""
        response = (
            self.client.schema(self.schema)
            .table("conversation_pathway_state")
            .select("*")
            .eq("conversation_id", conversation_id)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return None
        row = rows[0]
        return PathwayState(
            conversation_id=row["conversation_id"],
            pathway_code=row.get("pathway_code"),
            gathered_fields=row.get("gathered_fields") or {},
            current_question_code=row.get("current_question_code"),
            triggered_red_flags=row.get("triggered_red_flags") or [],
        )

    def save_state(self, conversation_id: str, state: PathwayState) -> None:
        """Upsert the full pathway state for a conversation."""
        payload = {
            "conversation_id": conversation_id,
            "pathway_code": state.pathway_code,
            "gathered_fields": state.gathered_fields,
            "current_question_code": state.current_question_code,
            "triggered_red_flags": state.triggered_red_flags,
            "updated_at": "now()",
        }
        (
            self.client.schema(self.schema)
            .table("conversation_pathway_state")
            .upsert(payload, on_conflict="conversation_id")
            .execute()
        )

    def update_gathered_fields(
        self, conversation_id: str, fields: dict
    ) -> None:
        """Merge new fields into the existing gathered_fields JSONB column."""
        existing = self.get_state(conversation_id)
        if existing is None:
            # No state row yet — create one with just the gathered fields
            self.save_state(
                conversation_id,
                PathwayState(
                    conversation_id=conversation_id,
                    gathered_fields=fields,
                ),
            )
            return

        merged = {**existing.gathered_fields, **fields}
        (
            self.client.schema(self.schema)
            .table("conversation_pathway_state")
            .update({"gathered_fields": merged, "updated_at": "now()"})
            .eq("conversation_id", conversation_id)
            .execute()
        )
