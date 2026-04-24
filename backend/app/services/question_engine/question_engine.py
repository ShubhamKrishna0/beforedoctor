import json
import logging

from openai import AsyncOpenAI

from app.repositories.question_bank_repository import QuestionBankRepository

logger = logging.getLogger(__name__)

MAX_QUESTIONS = 3


class QuestionEngine:
    def __init__(
        self,
        question_bank_repository: QuestionBankRepository,
        openai_client: AsyncOpenAI,
    ) -> None:
        self.question_bank_repository = question_bank_repository
        self.openai_client = openai_client

    async def get_questions(
        self,
        symptom_text: str,
        conversation_history: list[dict],
        user_medical_context: dict | None,
    ) -> list[str]:
        """Return 1-3 clarifying questions for the given symptom.

        Strategy:
        1. Try the QuestionBank first.
        2. Filter out questions already answered in conversation_history.
        3. If QuestionBank yields results, return up to 3.
        4. Otherwise fall back to LLM generation via OpenAI.
        """
        already_asked = self._extract_asked_questions(conversation_history)

        try:
            bank_questions = self._get_bank_questions(
                symptom_text, conversation_history, already_asked
            )
        except Exception:
            logger.exception("QuestionBank lookup failed, falling back to LLM")
            bank_questions = []

        if bank_questions:
            return bank_questions[:MAX_QUESTIONS]

        return await self._generate_questions_via_llm(
            symptom_text, conversation_history, user_medical_context
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_asked_questions(conversation_history: list[dict]) -> set[str]:
        """Collect question texts already posed by the assistant."""
        asked: set[str] = set()
        for msg in conversation_history:
            if msg.get("role") == "assistant":
                questions = msg.get("questions")
                if isinstance(questions, list):
                    asked.update(q.lower().strip() for q in questions if isinstance(q, str))
                content = msg.get("content", "")
                if isinstance(content, str) and "?" in content:
                    for line in content.splitlines():
                        line = line.strip()
                        if line.endswith("?"):
                            asked.add(line.lower())
        return asked

    def _get_bank_questions(
        self,
        symptom_text: str,
        conversation_history: list[dict],
        already_asked: set[str],
    ) -> list[str]:
        """Query the QuestionBank and filter already-asked questions."""
        conversation_context = self._build_conversation_context(conversation_history)
        rows = self.question_bank_repository.get_questions_for_symptom(
            symptom=symptom_text,
            conversation_context=conversation_context,
        )
        questions: list[str] = []
        for row in rows:
            q_text = row.get("question", "")
            if q_text.lower().strip() not in already_asked:
                questions.append(q_text)
        return questions

    @staticmethod
    def _build_conversation_context(conversation_history: list[dict]) -> dict:
        """Build a simple context dict from conversation history for condition evaluation."""
        context: dict = {}
        for msg in conversation_history:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    lower = content.lower()
                    if any(w in lower for w in ("day", "week", "hour", "month")):
                        context["duration"] = content
                    if any(w in lower for w in ("medication", "medicine", "taking", "drug")):
                        context["medications"] = content
        return context

    async def _generate_questions_via_llm(
        self,
        symptom_text: str,
        conversation_history: list[dict],
        user_medical_context: dict | None,
    ) -> list[str]:
        """Fall back to OpenAI to generate clarifying questions."""
        system_prompt = (
            "You are a medical triage assistant. Your job is to ask clarifying "
            "questions before providing a diagnosis. Given the user's symptom "
            "description and conversation history, generate 1 to 3 concise "
            "clarifying questions. Focus on: symptom duration, severity (1-10), "
            "existing medical conditions, and current medications — but skip "
            "topics the user already answered.\n"
            "Return ONLY a JSON array of question strings, e.g. "
            '[\"How long have you had this symptom?\", \"On a scale of 1-10, how severe is it?\"]'
        )

        messages: list[dict] = [{"role": "system", "content": system_prompt}]

        if user_medical_context:
            messages.append(
                {
                    "role": "system",
                    "content": f"User medical context: {json.dumps(user_medical_context)}",
                }
            )

        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": symptom_text})

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                temperature=0.3,
                max_tokens=300,
            )
            raw = response.choices[0].message.content or "[]"
            questions = json.loads(raw)
            if isinstance(questions, list) and questions:
                return [str(q) for q in questions[:MAX_QUESTIONS]]
        except Exception:
            logger.exception("LLM question generation failed")

        # Ultimate fallback: return generic questions
        return ["How long have you been experiencing this symptom?"]
