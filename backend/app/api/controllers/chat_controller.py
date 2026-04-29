import asyncio
import logging

from app.agents.doctor_agent.doctor_agent import DoctorAgent
from app.agents.orchestrator.llm_orchestrator import LLMOrchestrator
from app.agents.orchestrator.risk_detector import RiskDetector
from app.core.config.settings import get_settings
from app.repositories.conversation_pathway_state_repository import (
    ConversationPathwayStateRepository,
)
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.question_bank_repository import QuestionBankRepository
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse, DoctorResponsePayload
from app.services.answer_extractor.answer_extractor import AnswerExtractor
from app.services.audio_service.audio_service import AudioService
from app.services.medical_context.medical_context_service import MedicalContextService
from app.services.memory.memory_layer import MemoryLayer
from app.services.pathway_classifier.pathway_classifier import PathwayClassifier
from app.services.pathway_data.pathway_data_provider import PathwayDataProvider
from app.services.personalization.personalization_engine import PersonalizationEngine
from app.services.question_engine.pathway_question_engine import PathwayQuestionEngine
from app.services.question_engine.question_engine import QuestionEngine
from app.services.red_flag_evaluator.red_flag_evaluator import evaluate as red_flag_evaluate
from app.services.tts_service.tts_service import TTSService

logger = logging.getLogger(__name__)


class ChatController:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.conversation_repository = ConversationRepository()
        self.message_repository = MessageRepository()
        self.audio_service = AudioService()
        self.tts_service = TTSService()
        self.doctor_agent = DoctorAgent()

        # New orchestrator dependencies
        self.risk_detector = RiskDetector()
        self.medical_context_service = MedicalContextService()
        self.memory_layer = MemoryLayer()
        self.personalization_engine = PersonalizationEngine()

        # QuestionEngine needs an OpenAI client
        from app.services.ai_service.openai_client import get_openai_client

        openai_client = get_openai_client()
        question_bank_repo = QuestionBankRepository()
        self.question_engine = QuestionEngine(question_bank_repo, openai_client)

        # Pathway components
        self.pathway_data_provider = PathwayDataProvider()
        self.pathway_classifier = PathwayClassifier()
        self.pathway_question_engine = PathwayQuestionEngine()
        self.answer_extractor = AnswerExtractor()
        self.conversation_pathway_state_repository = ConversationPathwayStateRepository()

        self.orchestrator = LLMOrchestrator(
            risk_detector=self.risk_detector,
            question_engine=self.question_engine,
            medical_context_service=self.medical_context_service,
            memory_layer=self.memory_layer,
            personalization_engine=self.personalization_engine,
            doctor_agent=self.doctor_agent,
            pathway_data_provider=self.pathway_data_provider,
            pathway_classifier=self.pathway_classifier,
            pathway_question_engine=self.pathway_question_engine,
            answer_extractor=self.answer_extractor,
            red_flag_evaluator_fn=red_flag_evaluate,
            conversation_pathway_state_repository=self.conversation_pathway_state_repository,
        )

    def _resolve_conversation_id(self, user_id: str, conversation_id: str | None) -> str:
        if conversation_id and self.conversation_repository.conversation_exists_for_user(
            conversation_id, user_id
        ):
            return conversation_id
        return self.conversation_repository.create_conversation(user_id)

    async def send_message(
        self,
        user_id: str,
        payload: ChatMessageRequest,
    ) -> ChatMessageResponse:
        conversation_id = self._resolve_conversation_id(user_id, payload.conversation_id)

        # Persist the user message
        user_message_id = self.message_repository.create_message(
            conversation_id=conversation_id,
            role="user",
            text=payload.text,
        )

        # Retrieve conversation history and current phase from DB
        try:
            raw_messages = self.conversation_repository.get_conversation_messages(
                conversation_id
            )
            conversation_history = [
                {"role": msg.get("role", "user"), "content": msg.get("text", "")}
                for msg in raw_messages
                if msg.get("text")
            ]
        except Exception:
            logger.exception(
                "Failed to retrieve conversation history for %s, proceeding with current message only",
                conversation_id,
            )
            conversation_history = []

        current_phase = self.conversation_repository.get_conversation_phase(
            conversation_id
        )

        # Run the orchestrator pipeline
        result = await self.orchestrator.process_message(
            conversation_id=conversation_id,
            user_id=user_id,
            user_message=payload.text,
            conversation_history=conversation_history,
            current_phase=current_phase,
        )

        # Update conversation phase in DB
        if result.phase != current_phase:
            try:
                self.conversation_repository.update_conversation_phase(
                    conversation_id, result.phase
                )
            except Exception:
                logger.exception(
                    "Failed to update conversation phase for %s", conversation_id
                )

        # Build the response payload and AI message text
        response_payload: DoctorResponsePayload | None = None
        ai_message_text: str = ""
        audio_response_url: str | None = None

        if result.response:
            # Attach conversation_summary to the response payload
            resp_data = result.response.model_dump()
            resp_data["conversation_summary"] = result.conversation_summary
            response_payload = DoctorResponsePayload(**resp_data)
            ai_message_text = result.response.summary_of_symptoms

            # TTS for responding phase (backward compat with audio pipeline)
            if payload.generate_audio and self.settings.enable_tts:
                try:
                    tts_audio = await asyncio.wait_for(
                        self.tts_service.synthesize(
                            "\n".join(
                                [
                                    result.response.summary_of_symptoms,
                                    *result.response.immediate_advice,
                                    result.response.medical_disclaimer,
                                ]
                            )
                        ),
                        timeout=self.settings.tts_timeout_seconds,
                    )
                    audio_response_url = await asyncio.to_thread(
                        self.audio_service.upload_generated_audio,
                        user_id,
                        tts_audio,
                    )
                except Exception:
                    audio_response_url = None
        elif result.questions:
            ai_message_text = "\n".join(result.questions)

        # Persist AI message
        ai_message_id = self.message_repository.create_message(
            conversation_id=conversation_id,
            role="assistant",
            text=ai_message_text,
            audio_url=audio_response_url,
        )

        # Persist AI response JSON when we have a structured response
        if result.response:
            self.message_repository.create_ai_response(
                message_id=ai_message_id,
                response_json=result.response.model_dump(),
                audio_response_url=audio_response_url,
            )

        # Trigger personalization + memory extraction when transitioning out of responding
        if result.phase == "responding" and result.response:
            self._trigger_post_response_tasks(
                user_id, conversation_id, conversation_history, result
            )

        return ChatMessageResponse(
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            ai_message_id=ai_message_id,
            phase=result.phase,
            questions=result.questions,
            response=response_payload,
            audio_response_url=audio_response_url,
            is_urgent=result.is_urgent,
            smart_alerts=result.smart_alerts,
        )

    def _trigger_post_response_tasks(
        self,
        user_id: str,
        conversation_id: str,
        conversation_history: list[dict],
        result,
    ) -> None:
        """Fire-and-forget personalization and memory extraction after responding."""
        # Build conversation text for fact extraction
        conversation_text = "\n".join(
            f"{msg.get('role', 'user')}: {msg.get('content', '')}"
            for msg in conversation_history
        )

        # Extract symptoms/conditions from the response for profile update
        symptoms: list[str] = []
        conditions: list[str] = []
        if result.response:
            if result.response.summary_of_symptoms:
                symptoms.append(result.response.summary_of_symptoms)
            conditions.extend(result.response.possible_causes or [])

        async def _run_post_tasks():
            try:
                await self.personalization_engine.update_profile(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    symptoms=symptoms,
                    conditions=conditions,
                )
            except Exception:
                logger.exception("Post-response profile update failed for user %s", user_id)

            try:
                await self.memory_layer.extract_and_store_facts(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    conversation_text=conversation_text,
                )
            except Exception:
                logger.exception("Post-response fact extraction failed for user %s", user_id)

        asyncio.ensure_future(_run_post_tasks())
