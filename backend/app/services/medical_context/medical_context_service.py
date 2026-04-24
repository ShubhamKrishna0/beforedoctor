import asyncio
import logging
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from app.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class MedicalContext(BaseModel):
    prior_symptoms: list[dict] = Field(default_factory=list)
    prior_responses: list[dict] = Field(default_factory=list)
    symptom_frequencies: dict[str, int] = Field(default_factory=dict)


def _empty_context() -> MedicalContext:
    return MedicalContext()


class MedicalContextService:
    TIMEOUT_SECONDS: float = 3.0
    MAX_PRIOR_RESPONSES: int = 20

    async def get_context(self, user_id: str) -> MedicalContext:
        """Retrieve medical context for a user with a 3-second timeout.

        Returns an empty context on timeout or any error.
        """
        try:
            return await asyncio.wait_for(
                self._fetch_context(user_id),
                timeout=self.TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Medical context retrieval timed out after %.1fs for user %s",
                self.TIMEOUT_SECONDS,
                user_id,
            )
            return _empty_context()
        except Exception:
            logger.exception("Medical context retrieval failed for user %s", user_id)
            return _empty_context()

    async def _fetch_context(self, user_id: str) -> MedicalContext:
        """Core retrieval logic run inside the timeout wrapper."""
        client = get_supabase_client()
        schema = "before_doctor"
        now = datetime.now(timezone.utc)
        ninety_days_ago = (now - timedelta(days=90)).isoformat()
        seven_days_ago = (now - timedelta(days=7)).isoformat()

        # 1. Retrieve user's conversations from the last 90 days
        conversations_resp = (
            client.schema(schema)
            .table("conversations")
            .select("id")
            .eq("user_id", user_id)
            .gte("created_at", ninety_days_ago)
            .execute()
        )
        conversation_ids = [c["id"] for c in (conversations_resp.data or [])]

        if not conversation_ids:
            return _empty_context()

        # 2. Retrieve user messages (symptoms) from those conversations
        messages_resp = (
            client.schema(schema)
            .table("messages")
            .select("text, created_at, conversation_id")
            .in_("conversation_id", conversation_ids)
            .eq("role", "user")
            .order("created_at", desc=True)
            .execute()
        )
        user_messages = messages_resp.data or []

        prior_symptoms: list[dict] = [
            {
                "text": msg["text"],
                "created_at": msg["created_at"],
                "conversation_id": msg["conversation_id"],
            }
            for msg in user_messages
            if msg.get("text")
        ]

        # 3. Retrieve at most 20 most recent AI responses, ordered by created_at DESC
        #    ai_responses are linked via messages, so join through message_id
        ai_responses_resp = (
            client.schema(schema)
            .table("ai_responses")
            .select("id, response_json, created_at, message_id")
            .order("created_at", desc=True)
            .execute()
        )
        all_ai_responses = ai_responses_resp.data or []

        # Filter to only responses belonging to this user's conversations
        # Build a set of message_ids from the user's conversations
        all_messages_resp = (
            client.schema(schema)
            .table("messages")
            .select("id")
            .in_("conversation_id", conversation_ids)
            .execute()
        )
        valid_message_ids = {m["id"] for m in (all_messages_resp.data or [])}

        prior_responses: list[dict] = []
        for resp in all_ai_responses:
            if resp.get("message_id") in valid_message_ids:
                prior_responses.append(
                    {
                        "id": resp["id"],
                        "response_json": resp["response_json"],
                        "created_at": resp["created_at"],
                    }
                )
                if len(prior_responses) >= self.MAX_PRIOR_RESPONSES:
                    break

        # 4. Compute symptom_frequencies: symptom text → count in last 7 days
        symptom_frequencies: dict[str, int] = {}
        for msg in user_messages:
            if msg.get("text") and msg.get("created_at", "") >= seven_days_ago:
                symptom_text = msg["text"].strip().lower()
                symptom_frequencies[symptom_text] = (
                    symptom_frequencies.get(symptom_text, 0) + 1
                )

        return MedicalContext(
            prior_symptoms=prior_symptoms,
            prior_responses=prior_responses,
            symptom_frequencies=symptom_frequencies,
        )

    @staticmethod
    def format_for_prompt(context: MedicalContext) -> str:
        """Format the medical context into a string block for LLM prompt injection."""
        if not context.prior_symptoms and not context.prior_responses:
            return ""

        parts: list[str] = ["--- MEDICAL CONTEXT ---"]

        if context.prior_symptoms:
            parts.append("\n[Prior Symptoms]")
            for symptom in context.prior_symptoms:
                parts.append(
                    f"- {symptom.get('created_at', 'unknown date')}: "
                    f"{symptom.get('text', '')}"
                )

        if context.prior_responses:
            parts.append("\n[Prior AI Responses]")
            for resp in context.prior_responses:
                resp_json = resp.get("response_json", {})
                summary = resp_json.get("summary_of_symptoms", "N/A") if isinstance(resp_json, dict) else "N/A"
                parts.append(
                    f"- {resp.get('created_at', 'unknown date')}: {summary}"
                )

        if context.symptom_frequencies:
            parts.append("\n[Symptom Frequencies - Last 7 Days]")
            for symptom, count in context.symptom_frequencies.items():
                parts.append(f"- {symptom}: {count} time(s)")

        parts.append("\n--- END MEDICAL CONTEXT ---")
        return "\n".join(parts)
