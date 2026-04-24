import json
import logging
import uuid

from pydantic import BaseModel

from app.database.supabase_client import get_supabase_client
from app.services.ai_service.openai_client import get_openai_client

logger = logging.getLogger(__name__)

VALID_FACT_TYPES = frozenset(
    ["chronic_condition", "allergy", "medication", "recurring_symptom"]
)

EXTRACTION_SYSTEM_PROMPT = (
    "You are a medical fact extractor. Given a conversation between a user and "
    "a medical assistant, extract any long-term medical facts mentioned by the user. "
    "Return a JSON array of objects, each with:\n"
    '  - "fact_type": one of "chronic_condition", "allergy", "medication", "recurring_symptom"\n'
    '  - "fact_value": a short description of the fact\n'
    "Only include facts explicitly stated by the user. "
    "If no facts are found, return an empty array []."
)


class MedicalFact(BaseModel):
    id: str
    fact_type: str  # chronic_condition | allergy | medication | recurring_symptom
    fact_value: str
    source_conversation_id: str
    is_active: bool


class MemoryLayer:
    async def get_active_facts(self, user_id: str) -> list[MedicalFact]:
        """Return only active medical facts for the given user."""
        try:
            client = get_supabase_client()
            resp = (
                client.schema("before_doctor")
                .table("user_medical_memory")
                .select("id, fact_type, fact_value, source_conversation_id, is_active")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .execute()
            )
            return [
                MedicalFact(
                    id=str(row["id"]),
                    fact_type=row["fact_type"],
                    fact_value=row["fact_value"],
                    source_conversation_id=str(row["source_conversation_id"]),
                    is_active=row["is_active"],
                )
                for row in (resp.data or [])
            ]
        except Exception:
            logger.exception(
                "Failed to retrieve active facts for user %s", user_id
            )
            return []

    async def extract_and_store_facts(
        self,
        user_id: str,
        conversation_id: str,
        conversation_text: str,
    ) -> list[MedicalFact]:
        """Use LLM to extract medical facts from conversation text, then persist them."""
        try:
            extracted = await self._extract_facts_via_llm(conversation_text)
            if not extracted:
                return []
            return await self._persist_facts(user_id, conversation_id, extracted)
        except Exception:
            logger.exception(
                "Failed to extract/store facts for user %s, conversation %s",
                user_id,
                conversation_id,
            )
            return []

    async def deactivate_fact(self, fact_id: str) -> None:
        """Set is_active=false for the given fact."""
        try:
            client = get_supabase_client()
            client.schema("before_doctor").table("user_medical_memory").update(
                {"is_active": False}
            ).eq("id", fact_id).execute()
        except Exception:
            logger.exception("Failed to deactivate fact %s", fact_id)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _extract_facts_via_llm(
        self, conversation_text: str
    ) -> list[dict]:
        """Call OpenAI to extract medical facts from conversation text."""
        openai_client = get_openai_client()
        response = await openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": conversation_text},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "[]"
        parsed = json.loads(raw)

        # Handle both {"facts": [...]} and plain [...]
        if isinstance(parsed, dict):
            parsed = parsed.get("facts", [])
        if not isinstance(parsed, list):
            return []

        # Validate each extracted fact
        valid: list[dict] = []
        for item in parsed:
            ft = item.get("fact_type", "")
            fv = item.get("fact_value", "")
            if ft in VALID_FACT_TYPES and fv:
                valid.append({"fact_type": ft, "fact_value": fv})
        return valid

    async def _persist_facts(
        self,
        user_id: str,
        conversation_id: str,
        facts: list[dict],
    ) -> list[MedicalFact]:
        """Insert extracted facts into user_medical_memory and return models."""
        client = get_supabase_client()
        rows = [
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "fact_type": f["fact_type"],
                "fact_value": f["fact_value"],
                "source_conversation_id": conversation_id,
                "is_active": True,
            }
            for f in facts
        ]
        client.schema("before_doctor").table("user_medical_memory").insert(
            rows
        ).execute()

        return [
            MedicalFact(
                id=row["id"],
                fact_type=row["fact_type"],
                fact_value=row["fact_value"],
                source_conversation_id=row["source_conversation_id"],
                is_active=True,
            )
            for row in rows
        ]
