from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from app.models.pathway_models import PathwayState
    from app.repositories.conversation_pathway_state_repository import (
        ConversationPathwayStateRepository,
    )
    from app.services.answer_extractor.answer_extractor import AnswerExtractor
    from app.services.pathway_classifier.pathway_classifier import PathwayClassifier
    from app.services.pathway_data.pathway_data_provider import PathwayDataProvider
    from app.services.question_engine.pathway_question_engine import (
        PathwayQuestionEngine,
    )

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
        # --- Pathway components (optional — None preserves legacy behaviour) ---
        pathway_data_provider: PathwayDataProvider | None = None,
        pathway_classifier: PathwayClassifier | None = None,
        pathway_question_engine: PathwayQuestionEngine | None = None,
        answer_extractor: AnswerExtractor | None = None,
        red_flag_evaluator_fn=None,  # callable: evaluate(gathered_fields, rules) -> list[RedFlagResult]
        conversation_pathway_state_repository: ConversationPathwayStateRepository | None = None,
    ) -> None:
        self.risk_detector = risk_detector
        self.question_engine = question_engine
        self.medical_context_service = medical_context_service
        self.memory_layer = memory_layer
        self.personalization_engine = personalization_engine
        self.doctor_agent = doctor_agent

        # Pathway components — all optional for backward compatibility
        self.pathway_data_provider = pathway_data_provider
        self.pathway_classifier = pathway_classifier
        self.pathway_question_engine = pathway_question_engine
        self.answer_extractor = answer_extractor
        self._red_flag_evaluate = red_flag_evaluator_fn
        self.pathway_state_repo = conversation_pathway_state_repository

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
        # 4b. Pathway pipeline (if components are wired)
        # ------------------------------------------------------------------
        if self._pathway_components_available():
            pathway_result = await self._try_pathway_pipeline(
                conversation_id=conversation_id,
                user_id=user_id,
                user_message=user_message,
                conversation_history=conversation_history,
                medical_context=medical_context,
                active_facts=active_facts,
                profile_summary=profile_summary,
                symptom_classification=symptom_classification,
                smart_alerts=smart_alerts,
            )
            if pathway_result is not None:
                return pathway_result
            # pathway_result is None → classification failed, fall through to legacy

        # ------------------------------------------------------------------
        # 5. Phase transition logic (legacy path)
        # ------------------------------------------------------------------
        effective_phase = self._resolve_phase(
            current_phase, conversation_history
        )

        # ------------------------------------------------------------------
        # 6. Question-or-response decision (legacy path)
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
    # Pathway pipeline helpers
    # ==================================================================

    def _pathway_components_available(self) -> bool:
        """Return True when all pathway components have been wired."""
        return all([
            self.pathway_data_provider is not None,
            self.pathway_classifier is not None,
            self.pathway_question_engine is not None,
            self.answer_extractor is not None,
            self._red_flag_evaluate is not None,
            self.pathway_state_repo is not None,
        ])

    async def _try_pathway_pipeline(
        self,
        conversation_id: str,
        user_id: str,
        user_message: str,
        conversation_history: list[dict],
        medical_context,
        active_facts: list,
        profile_summary: str,
        symptom_classification: str | None,
        smart_alerts: list[str],
    ) -> OrchestratorResult | None:
        """Run the pathway-driven pipeline.

        Returns an ``OrchestratorResult`` when the pathway is active, or
        ``None`` to signal the caller to fall back to legacy behaviour.
        """
        assert self.pathway_data_provider is not None
        assert self.pathway_classifier is not None
        assert self.pathway_question_engine is not None
        assert self.answer_extractor is not None
        assert self._red_flag_evaluate is not None
        assert self.pathway_state_repo is not None

        # --- Load (or initialise) pathway state ---
        try:
            pathway_state = self.pathway_state_repo.get_state(conversation_id)
        except Exception:
            logger.exception("Failed to load pathway state for %s, falling back to legacy", conversation_id)
            return None

        # --- First message: classify the pathway ---
        if pathway_state is None:
            available = self.pathway_data_provider.get_all_pathway_codes()
            if not available:
                return None  # No pathway data → legacy fallback

            try:
                pathway_code = await self.pathway_classifier.classify(
                    user_message, available
                )
            except Exception:
                logger.exception("Pathway classification failed, falling back to legacy")
                return None

            if pathway_code is None:
                return None  # Classification failed → legacy fallback

            from app.models.pathway_models import PathwayState as _PS

            pathway_state = _PS(
                conversation_id=conversation_id,
                pathway_code=pathway_code,
            )

        # At this point we have a pathway_code
        pathway_code = pathway_state.pathway_code
        if pathway_code is None:
            return None  # Shouldn't happen, but guard

        # --- Answer extraction ---
        required_fields = self.pathway_data_provider.get_required_fields(pathway_code)
        current_question_code = pathway_state.current_question_code

        # Determine the target field for extraction (the field we last asked about)
        target_field = None
        if current_question_code:
            templates = self.pathway_data_provider.get_question_templates(pathway_code)
            for t in templates:
                if t.question_code == current_question_code:
                    for rf in required_fields:
                        if rf.field_code == t.field_code:
                            target_field = rf
                            break
                    break

        # If no target field yet (first message), pick the first required field
        if target_field is None and required_fields:
            target_field = required_fields[0]

        if target_field is not None:
            try:
                extracted = await self.answer_extractor.extract(
                    user_text=user_message,
                    target_field=target_field,
                    all_pathway_fields=required_fields,
                    gathered_fields=pathway_state.gathered_fields,
                )
            except Exception:
                logger.exception("Answer extraction failed, re-asking same question")
                extracted = {}

            if extracted:
                pathway_state.gathered_fields.update(extracted)

        # --- Red flag evaluation ---
        red_flag_rules = self.pathway_data_provider.get_red_flag_rules(pathway_code)
        try:
            triggered_flags = self._red_flag_evaluate(
                pathway_state.gathered_fields, red_flag_rules
            )
        except Exception:
            logger.exception("Red flag evaluation failed, continuing gathering")
            triggered_flags = []

        # Store triggered flags
        if triggered_flags:
            pathway_state.triggered_red_flags = [
                {"rule_code": f.rule_code, "urgency_level": f.urgency_level, "message": f.message}
                for f in triggered_flags
            ]

        # --- Check for emergency red flag → immediate escalation ---
        emergency_flags = [f for f in triggered_flags if f.urgency_level == "emergency"]
        if emergency_flags:
            self._save_pathway_state_safe(conversation_id, pathway_state)
            escalation_msg = emergency_flags[0].message
            return OrchestratorResult(
                phase="responding",
                questions=None,
                response=DoctorResponsePayload(
                    summary_of_symptoms=escalation_msg,
                    possible_causes=[],
                    immediate_advice=[
                        escalation_msg,
                        "Please seek emergency medical care immediately.",
                    ],
                    lifestyle_suggestions=[],
                    warning_signs=[escalation_msg],
                    when_to_see_a_real_doctor="Seek emergency care NOW.",
                    medical_disclaimer=(
                        "This AI assistant is not a substitute for professional medical advice. "
                        "If this is an emergency, call emergency services immediately."
                    ),
                    follow_up_questions=[],
                ),
                is_urgent=True,
                symptom_classification=symptom_classification,
                smart_alerts=smart_alerts,
            )

        # --- Check for urgent red flag → transition to responding with urgency ---
        urgent_flags = [f for f in triggered_flags if f.urgency_level == "urgent"]
        if urgent_flags:
            self._save_pathway_state_safe(conversation_id, pathway_state)
            urgency_context = "; ".join(f.message for f in urgent_flags)
            return await self._handle_pathway_responding(
                user_id=user_id,
                user_message=user_message,
                conversation_history=conversation_history,
                medical_context=medical_context,
                active_facts=active_facts,
                profile_summary=profile_summary,
                symptom_classification=symptom_classification,
                smart_alerts=smart_alerts,
                gathered_fields=pathway_state.gathered_fields,
                pathway_code=pathway_code,
                urgency_context=urgency_context,
            )

        # --- No red flag: check if gathering is complete ---
        question_result = self.pathway_question_engine.next_question(
            pathway_code=pathway_code,
            gathered_fields=pathway_state.gathered_fields,
            pathway_data=self.pathway_data_provider,
        )

        if question_result.is_complete:
            # All required fields gathered → transition to responding
            self._save_pathway_state_safe(conversation_id, pathway_state)
            return await self._handle_pathway_responding(
                user_id=user_id,
                user_message=user_message,
                conversation_history=conversation_history,
                medical_context=medical_context,
                active_facts=active_facts,
                profile_summary=profile_summary,
                symptom_classification=symptom_classification,
                smart_alerts=smart_alerts,
                gathered_fields=pathway_state.gathered_fields,
                pathway_code=pathway_code,
            )

        # --- More questions needed: return the single question ---
        # Update current_question_code for next turn's extraction target
        if question_result.field_code:
            templates = self.pathway_data_provider.get_question_templates(pathway_code)
            for t in templates:
                if t.field_code == question_result.field_code:
                    pathway_state.current_question_code = t.question_code
                    break

        self._save_pathway_state_safe(conversation_id, pathway_state)

        return OrchestratorResult(
            phase="gathering",
            questions=[question_result.question_text] if question_result.question_text else [],
            is_urgent=False,
            symptom_classification=symptom_classification,
            smart_alerts=smart_alerts,
        )

    async def _handle_pathway_responding(
        self,
        user_id: str,
        user_message: str,
        conversation_history: list[dict],
        medical_context,
        active_facts: list,
        profile_summary: str,
        symptom_classification: str | None,
        smart_alerts: list[str],
        gathered_fields: dict,
        pathway_code: str,
        urgency_context: str | None = None,
    ) -> OrchestratorResult:
        """Transition to responding with gathered pathway fields included in the prompt."""
        try:
            response_dict = await self._generate_doctor_response_with_context(
                user_id=user_id,
                user_message=user_message,
                conversation_history=conversation_history,
                medical_context=medical_context,
                active_facts=active_facts,
                profile_summary=profile_summary,
                is_urgent=urgency_context is not None,
                gathered_fields=gathered_fields,
                pathway_code=pathway_code,
                urgency_context=urgency_context,
            )
            response = DoctorResponsePayload(**response_dict)
        except Exception:
            logger.exception("Failed to generate pathway response, using safe fallback")
            response = _SAFE_RESPONSE

        conversation_summary = self._build_conversation_summary(conversation_history)

        return OrchestratorResult(
            phase="responding",
            response=response,
            conversation_summary=conversation_summary,
            is_urgent=urgency_context is not None,
            symptom_classification=symptom_classification,
            smart_alerts=smart_alerts,
        )

    def _save_pathway_state_safe(self, conversation_id: str, state: PathwayState) -> None:
        """Persist pathway state, logging but not raising on failure."""
        try:
            assert self.pathway_state_repo is not None
            self.pathway_state_repo.save_state(conversation_id, state)
        except Exception:
            logger.exception("Failed to save pathway state for %s", conversation_id)

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
        gathered_fields: dict | None = None,
        pathway_code: str | None = None,
        urgency_context: str | None = None,
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

        # Include pathway gathered fields in the prompt
        if gathered_fields and pathway_code:
            fields_text = "\n".join(f"  - {k}: {v}" for k, v in gathered_fields.items())
            system_prompt += (
                f"\n\n--- PATHWAY DATA (pathway: {pathway_code}) ---\n"
                f"The following clinical information was gathered during the intake:\n"
                f"{fields_text}\n"
                f"--- END PATHWAY DATA ---"
            )

        if urgency_context:
            system_prompt += (
                f"\n\nURGENCY ALERT: {urgency_context}\n"
                "Include this urgency information prominently in your response."
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
