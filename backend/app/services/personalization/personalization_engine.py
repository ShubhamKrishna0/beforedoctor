import logging
from datetime import datetime, timezone

from app.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class PersonalizationEngine:
    """Maintains and retrieves user profile data for prompt personalization.

    Profile data JSONB structure:
    {
        "symptoms": {"headache": 5, "fever": 2, ...},
        "conditions": ["diabetes", "asthma", ...],
        "total_conversations": 10,
        "last_conversation_id": "uuid"
    }
    """

    async def get_profile_summary(self, user_id: str) -> str:
        """Return a text summary of the user's profile.

        Returns an empty string when no profile exists or on any error.
        """
        try:
            client = get_supabase_client()
            resp = (
                client.schema("before_doctor")
                .table("user_profiles")
                .select("profile_data")
                .eq("user_id", user_id)
                .execute()
            )
            rows = resp.data or []
            if not rows:
                return ""

            profile_data = rows[0].get("profile_data") or {}
            return self._format_summary(profile_data)
        except Exception:
            logger.exception(
                "Failed to retrieve profile summary for user %s", user_id
            )
            return ""

    async def update_profile(
        self,
        user_id: str,
        conversation_id: str,
        symptoms: list[str],
        conditions: list[str],
    ) -> None:
        """Upsert user_profiles row, merging new symptoms and conditions."""
        try:
            client = get_supabase_client()
            schema = "before_doctor"

            # Fetch existing profile
            resp = (
                client.schema(schema)
                .table("user_profiles")
                .select("id, profile_data")
                .eq("user_id", user_id)
                .execute()
            )
            existing_rows = resp.data or []

            if existing_rows:
                existing = existing_rows[0]
                profile_data = existing.get("profile_data") or {}
                merged = self._merge_profile(
                    profile_data, symptoms, conditions, conversation_id
                )
                (
                    client.schema(schema)
                    .table("user_profiles")
                    .update(
                        {
                            "profile_data": merged,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    .eq("id", existing["id"])
                    .execute()
                )
            else:
                new_profile = self._build_new_profile(
                    symptoms, conditions, conversation_id
                )
                (
                    client.schema(schema)
                    .table("user_profiles")
                    .insert(
                        {
                            "user_id": user_id,
                            "profile_data": new_profile,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    .execute()
                )
        except Exception:
            logger.exception(
                "Failed to update profile for user %s, conversation %s",
                user_id,
                conversation_id,
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_profile(
        existing: dict,
        new_symptoms: list[str],
        new_conditions: list[str],
        conversation_id: str,
    ) -> dict:
        """Merge new symptoms/conditions into an existing profile_data dict."""
        symptoms: dict[str, int] = dict(existing.get("symptoms", {}))
        for s in new_symptoms:
            key = s.strip().lower()
            if key:
                symptoms[key] = symptoms.get(key, 0) + 1

        conditions_set: set[str] = set(existing.get("conditions", []))
        for c in new_conditions:
            val = c.strip().lower()
            if val:
                conditions_set.add(val)

        total = existing.get("total_conversations", 0) + 1

        return {
            "symptoms": symptoms,
            "conditions": sorted(conditions_set),
            "total_conversations": total,
            "last_conversation_id": conversation_id,
        }

    @staticmethod
    def _build_new_profile(
        symptoms: list[str],
        conditions: list[str],
        conversation_id: str,
    ) -> dict:
        """Create a fresh profile_data dict from the first conversation."""
        symptom_counts: dict[str, int] = {}
        for s in symptoms:
            key = s.strip().lower()
            if key:
                symptom_counts[key] = symptom_counts.get(key, 0) + 1

        unique_conditions = sorted(
            {c.strip().lower() for c in conditions if c.strip()}
        )

        return {
            "symptoms": symptom_counts,
            "conditions": unique_conditions,
            "total_conversations": 1,
            "last_conversation_id": conversation_id,
        }

    @staticmethod
    def _format_summary(profile_data: dict) -> str:
        """Format profile_data into a human-readable summary string."""
        parts: list[str] = []

        symptoms = profile_data.get("symptoms", {})
        if symptoms:
            top_symptoms = sorted(
                symptoms.items(), key=lambda x: x[1], reverse=True
            )
            symptom_strs = [
                f"{name} ({count}x)" for name, count in top_symptoms
            ]
            parts.append(f"Reported symptoms: {', '.join(symptom_strs)}")

        conditions = profile_data.get("conditions", [])
        if conditions:
            parts.append(f"Known conditions: {', '.join(conditions)}")

        total = profile_data.get("total_conversations", 0)
        if total:
            parts.append(f"Total conversations: {total}")

        return ". ".join(parts)
