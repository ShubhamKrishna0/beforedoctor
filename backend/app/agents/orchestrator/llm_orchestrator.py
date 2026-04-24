import json
import logging

from pydantic import BaseModel

from app.agents.doctor_agent.doctor_agent import DoctorAgent
from app.agents.doctor_agent.doctor_prompt import build_doctor_system_prompt
from app.agents.doctor_agent.doctor_rules import SAFETY_RULES
from app.agents.orchestrator.risk_detector import RiskDetector
from app.core.config.settings import get_settings
from app.schemas.chat import DoctorResponsePayload
from app.services.medical_context.medical_context_service import (
    MedicalContextService,
)
from app.services.memory.memory_layer import MemoryLayer
from app.services.personalization.personalization_engine import (
    PersonalizationEngine,
)
from app.services.question_engine.question_engine import QuestionEngine

logger = logging.getLogger(__name__)

# Minimum rounds of user messages before auto-transitioning to responding
_MIN_GATHERING_ROUNDS = 2

# Smart alert threshold: symptom reported >= this many times in 7 days
_SMART_ALERT_THRESHOLD = 3

VALID_SYMPTOM_CLASSIFICATIONS = frozenset(
    ["previously_reported", "common", "new_unknown"]
)

CLASSIFICATION_SYSTEM_PROMPT = (
    "You are a symptom classifier. Given a user message describing symptoms "
    "and their medical history, classify the symptom into exactly one category.\n"
    "Return ONLY a JSON object with a single key \"classification\" whose value "
    "is one of: \"previously_reported\", \"common\", \"new_unknown\".\n\n"
    "- \"previously_reported\": The user has reported this same symptom before "
    "(based on their medical history).\n"
    "- \"common\": The symptom is a well-known, frequently occurring condition "
    "(e.g., headache, fever, cough) even if the user hasn't reported it before.\n"
    "- \"new_unknown\": The symptom is unusual or not easily categorized.\n"
)

_SAFE_RESPONSE = DoctorResponsePayload(
    summary_of_symptoms="We were unable to fully process your symptoms at this time.",
    possible_causes=["Unable to determine — please consult a healthcare professional."],
    immediate_advice=[
        "If you are experiencing severe symptoms, please seek emergency care immediately.",
        "Try again in a few minutes, or contact your healthcare provider directly.",
    ],
    lifestyle_suggestions=[],
    warning_signs=[
        "Chest pain, difficulty breathing, sudden numbness, or loss of consciousness "
        "require immediate emergency care."
    ],
    when_to_see_a_real_doctor=(
        "Please consult a licensed healthcare professional for a proper evaluation. "
        "If your symptoms are severe or worsening, visit an emergency room or call "
        "emergency services right away."
    ),
    medical_disclaimer=(
        "This AI assistant is not a substitute for professional medical advice, "
        "diagnosis, or treatment. Always seek the advice of a qualified healthcare "
        "provider with any questions you may have regarding a medical condition."
    ),
    follow_up_questions=[],
)


class OrchestratorResult(BaseModel):
    phase: str  # "gathering" | "responding" | "follow_up"
    questions: list[str] | None = None
    response: DoctorResponsePayload | None = None
    conversation_summary: str | None = None
    is_urgent: bool = False
    symptom_classification: str | None = None
    smart_alerts: list[str] = []


class LLMOrchestrator:
    """Central pipeline coordinator.

    Executes: risk detection → context fetch → symptom classification →
    question-or-response decision → output.
    """

    def __init__(
        self,
        risk_detector: RiskDetector,
        question_engine: QuestionEngine,
        medical_context_service: MedicalContextService,
        memory_layer: MemoryLayer,
        personalization_engine: PersonalizationEngine,
        doctor_agent: DoctorAgent,
    ) -> None:
        self.risk_detector = risk_detector
        self.question_engine = question_engine
        self.medical_context_service = medical_context_service
        self.memory_layer = memory_layer
        self.personalization_engine = personalization_engine
        self.doctor_agent = doctor_agent

    async def process_message(
        self,
        conversation_id: str,
        user_id: str,
        user_message: str,
        conversation_history: list[dict],
        current_phase: str,
    ) -> OrchestratorResult:
        """Execute the full orchestration pipeline and return a result."""

        # ------------------------------------------------------------------
        # 1. Risk detection — FIRST before anything else (Req 8.4)
        # ------------------------------------------------------------------
        risk_result = self.risk_detector.evaluate(user_message)

        if risk_result.is_urgent:
            return await self._handle_urgent(
                user_id, user_message, conversation_history, risk_result
            )

        # ------------------------------------------------------------------
        # 2. Context fetch (parallel where possible)
        # ------------------------------------------------------------------
        medical_context = await self.medical_context_service.get_context(user_id)
        active_facts = await self.memory_layer.get_active_facts(user_id)
        profile_summary = await self.personalization_engine.get_profile_summary(
            user_id
        )

        # ------------------------------------------------------------------
        # 3. Smart alerts — symptom_frequencies >= threshold in 7 days
        # ------------------------------------------------------------------
        smart_alerts = self._compute_smart_alerts(medical_context.symptom_frequencies)

        # ------------------------------------------------------------------
        # 4. Symptom classification via LLM
        # ------------------------------------------------------------------
        symptom_classification = await self._classify_symptom(
            user_message, medical_context, active_facts
        )

        # ------------------------------------------------------------------
        # 5. Phase transition logic
        # ------------------------------------------------------------------
        effective_phase = self._resolve_phase(
            current_phase, conversation_history
        )

        # ------------------------------------------------------------------
        # 6. Question-or-response decision
        # ------------------------------------------------------------------
        if effective_phase == "gathering":
            return await self._handle_gathering(
                user_message,
                conversation_history,
                medical_context,
                symptom_classification,
                smart_alerts,
            )

        # Phase is "responding" or "follow_up"
        return await self._handle_responding(
            user_id,
            user_message,
            conversation_history,
            medical_context,
            active_facts,
            profile_summary,
            symptom_classification,
            smart_alerts,
        )

    # ==================================================================
    # Private helpers
    # ==================================================================

    async def _handle_urgent(
        self,
        user_id: str,
        user_message: str,
        conversation_history: list[dict],
        risk_result,
    ) -> OrchestratorResult:
        """Bypass gathering and produce an immediate Structured_Response."""
        try:
            response_dict = await self._generate_doctor_response_with_context(
                user_id=user_id,
                user_message=user_message,
                conversation_history=conversation_history,
                medical_context=None,
                active_facts=[],
                profile_summary="",
                is_urgent=True,
            )
            response = DoctorResponsePayload(**response_dict)
        except Exception:
            logger.exception("Failed to generate urgent response, using safe fallback")
            response = _SAFE_RESPONSE

        return OrchestratorResult(
            phase="responding",
            response=response,
            is_urgent=True,
            symptom_classification=None,
            smart_alerts=[],
        )

    async def _handle_gathering(
        self,
        user_message: str,
        conversation_history: list[dict],
        medical_context,
        symptom_classification: str | None,
        smart_alerts: list[str],
    ) -> OrchestratorResult:
        """Use QuestionEngine to get clarifying questions."""
        user_medical_context = (
            {
                "prior_symptoms": medical_context.prior_symptoms,
                "symptom_frequencies": medical_context.symptom_frequencies,
            }
            if medical_context
            else None
        )

        questions = await self.question_engine.get_questions(
            symptom_text=user_message,
            conversation_history=conversation_history,
            user_medical_context=user_medical_context,
        )

        return OrchestratorResult(
            phase="gathering",
            questions=questions,
            is_urgent=False,
            symptom_classification=symptom_classification,
            smart_alerts=smart_alerts,
        )

    async def _handle_responding(
        self,
        user_id: str,
        user_message: str,
        conversation_history: list[dict],
        medical_context,
        active_facts: list,
        profile_summary: str,
        symptom_classification: str | None,
        smart_alerts: list[str],
    ) -> OrchestratorResult:
        """Use DoctorAgent to generate a full Structured_Response with all context."""
        try:
            response_dict = await self._generate_doctor_response_with_context(
                user_id=user_id,
                user_message=user_message,
                conversation_history=conversation_history,
                medical_context=medical_context,
                active_facts=active_facts,
                profile_summary=profile_summary,
                is_urgent=False,
            )
            response = DoctorResponsePayload(**response_dict)
        except Exception:
            logger.exception(
                "Failed to generate response, using safe fallback"
            )
            response = _SAFE_RESPONSE

        # Build conversation summary from history
        conversation_summary = self._build_conversation_summary(
            conversation_history
        )

        return OrchestratorResult(
            phase="responding",
            response=response,
            conversation_summary=conversation_summary,
            is_urgent=False,
            symptom_classification=symptom_classification,
            smart_alerts=smart_alerts,
        )

    async def _generate_doctor_response_with_context(
        self,
        user_id: str,
        user_message: str,
        conversation_history: list[dict],
        medical_context,
        active_facts: list,
        profile_summary: str,
        is_urgent: bool,
    ) -> dict:
        """Build a context-enriched prompt and call DoctorAgent with fallback.

        Prompt component order (deterministic — Req 6.4):
        1. System prompt
        2. Safety rules
        3. Medical context
        4. Conversation history
        5. Current user message
        """
        settings = get_settings()
        from app.services.ai_service.openai_client import get_openai_client

        client = get_openai_client()

        # --- 1. System prompt ---
        system_prompt = build_doctor_system_prompt()
        if is_urgent:
            system_prompt += (
                "\n\nURGENT: The user may be experiencing a medical emergency. "
                "Advise them to seek immediate emergency care. Provide a concise, "
                "structured response with emergency guidance."
            )

        # --- 2. Safety rules ---
        safety_rules_text = "Medical safety rules:\n- " + "\n- ".join(SAFETY_RULES)

        # --- 3. Medical context ---
        medical_context_text = ""
        if medical_context:
            medical_context_text = MedicalContextService.format_for_prompt(
                medical_context
            )

        # Include active memory facts
        if active_facts:
            facts_lines = ["\n--- MEMORY FACTS ---"]
            for fact in active_facts:
                facts_lines.append(f"- [{fact.fact_type}] {fact.fact_value}")
            facts_lines.append("--- END MEMORY FACTS ---")
            medical_context_text += "\n".join(facts_lines)

        # Include profile summary
        if profile_summary:
            medical_context_text += f"\n\n--- USER PROFILE ---\n{profile_summary}\n--- END USER PROFILE ---"

        # --- Build messages in deterministic order ---
        from app.core.config.prompt_loader import load_prompt_config

        prompt_config = load_prompt_config()
        schema = {
            "type": "object",
            "properties": {
                "summary_of_symptoms": {"type": "string"},
                "possible_causes": {"type": "array", "items": {"type": "string"}},
                "immediate_advice": {"type": "array", "items": {"type": "string"}},
                "lifestyle_suggestions": {"type": "array", "items": {"type": "string"}},
                "warning_signs": {"type": "array", "items": {"type": "string"}},
                "when_to_see_a_real_doctor": {"type": "string"},
                "medical_disclaimer": {"type": "string"},
                "follow_up_questions": {"type": "array", "items": {"type": "string"}},
            },
            "required": prompt_config["response_sections"],
            "additionalProperties": False,
        }

        request_input: list[dict] = []

        # 1. System prompt
        request_input.append({"role": "system", "content": system_prompt})

        # 2. Safety rules
        request_input.append({"role": "developer", "content": safety_rules_text})

        # 3. Medical context
        if medical_context_text:
            request_input.append(
                {"role": "system", "content": medical_context_text}
            )

        # 4. Conversation history
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                request_input.append({"role": role, "content": content})

        # 5. Current user message
        request_input.append({"role": "user", "content": user_message})

        request_text = {
            "format": {
                "type": "json_schema",
                "name": "doctor_response",
                "schema": schema,
                "strict": True,
            }
        }

        import asyncio

        async def _create_response(model: str):
            return await asyncio.wait_for(
                client.responses.create(
                    model=model,
                    input=request_input,
                    text=request_text,
                ),
                timeout=settings.openai_doctor_timeout_seconds,
            )

        # Primary model attempt
        try:
            response = await _create_response(settings.openai_doctor_model)
            return json.loads(response.output_text)
        except Exception:
            logger.exception("Primary model failed, trying fallback")

        # Fallback model attempt
        fallback_model = settings.openai_doctor_fallback_model.strip()
        if fallback_model and fallback_model != settings.openai_doctor_model.strip():
            try:
                response = await _create_response(fallback_model)
                return json.loads(response.output_text)
            except Exception:
                logger.exception("Fallback model also failed")

        # Both failed — raise to let caller use safe response
        raise RuntimeError("Both primary and fallback LLM models failed")

    async def _classify_symptom(
        self,
        user_message: str,
        medical_context,
        active_facts: list,
    ) -> str | None:
        """Use LLM to classify the symptom as previously_reported | common | new_unknown."""
        try:
            from app.services.ai_service.openai_client import get_openai_client

            client = get_openai_client()

            history_summary = ""
            if medical_context and medical_context.prior_symptoms:
                prior_texts = [
                    s.get("text", "") for s in medical_context.prior_symptoms[:10]
                ]
                history_summary = "Prior symptoms: " + "; ".join(prior_texts)

            if active_facts:
                fact_texts = [f"{f.fact_type}: {f.fact_value}" for f in active_facts]
                history_summary += "\nMedical facts: " + "; ".join(fact_texts)

            messages: list[dict] = [
                {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
            ]
            if history_summary:
                messages.append(
                    {"role": "system", "content": f"User medical history:\n{history_summary}"}
                )
            messages.append({"role": "user", "content": user_message})

            response = await client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                temperature=0.0,
                max_tokens=50,
            )
            raw = response.choices[0].message.content or "{}"
            parsed = json.loads(raw)
            classification = parsed.get("classification", "new_unknown")

            if classification not in VALID_SYMPTOM_CLASSIFICATIONS:
                return "new_unknown"
            return classification
        except Exception:
            logger.exception("Symptom classification failed, defaulting to new_unknown")
            return "new_unknown"

    def _resolve_phase(
        self,
        current_phase: str,
        conversation_history: list[dict],
    ) -> str:
        """Determine effective phase, applying transition logic.

        Transition: gathering → responding when:
        - User has sent >= _MIN_GATHERING_ROUNDS messages, OR
        - Current phase is already 'responding' or 'follow_up'
        """
        if current_phase in ("responding", "follow_up"):
            return current_phase

        # Count user messages in conversation history
        user_message_count = sum(
            1 for msg in conversation_history if msg.get("role") == "user"
        )

        if user_message_count >= _MIN_GATHERING_ROUNDS:
            return "responding"

        return "gathering"

    @staticmethod
    def _compute_smart_alerts(
        symptom_frequencies: dict[str, int],
    ) -> list[str]:
        """Generate smart alerts for symptoms reported >= threshold times in 7 days."""
        alerts: list[str] = []
        for symptom, count in symptom_frequencies.items():
            if count >= _SMART_ALERT_THRESHOLD:
                alerts.append(
                    f"You have reported \"{symptom}\" {count} times this week. "
                    f"Consider discussing this pattern with your healthcare provider."
                )
        return alerts

    @staticmethod
    def _build_conversation_summary(conversation_history: list[dict]) -> str | None:
        """Build a brief summary of key facts from the conversation history."""
        if not conversation_history:
            return None

        user_messages = [
            msg.get("content", "")
            for msg in conversation_history
            if msg.get("role") == "user" and msg.get("content")
        ]
        if not user_messages:
            return None

        return "Key information provided: " + " | ".join(user_messages)
