from app.database.supabase_client import get_supabase_client


class QuestionBankRepository:
    def __init__(self) -> None:
        self.client = get_supabase_client()
        self.schema = "before_doctor"

    def get_questions_for_symptom(
        self, symptom: str, conversation_context: dict | None = None
    ) -> list[dict]:
        response = (
            self.client.schema(self.schema)
            .table("question_bank")
            .select("*")
            .ilike("symptom", symptom)
            .order("priority")
            .execute()
        )
        questions = response.data or []

        if conversation_context is not None:
            questions = [
                q
                for q in questions
                if self._conditions_met(q.get("conditions_to_ask"), conversation_context)
            ]

        return questions

    @staticmethod
    def _conditions_met(
        conditions_to_ask: dict | None, conversation_context: dict
    ) -> bool:
        """Evaluate conditions_to_ask JSONB against the conversation context.

        If conditions_to_ask is None or empty, the question is always included.
        Otherwise, every key inside the ``ask_if`` object must be satisfied by
        the conversation context for the question to be included.

        Supported condition values:
        - ``"any"`` — the key just needs to exist in the context (any value).
        - Any other string — the context value must match (case-insensitive).
        """
        if not conditions_to_ask:
            return True

        ask_if = conditions_to_ask.get("ask_if")
        if not ask_if or not isinstance(ask_if, dict):
            return True

        for key, expected in ask_if.items():
            context_value = conversation_context.get(key)

            if expected == "any":
                if context_value is None:
                    return False
            else:
                if context_value is None:
                    return False
                if str(context_value).lower() != str(expected).lower():
                    return False

        return True
