from app.agents.doctor_agent.doctor_agent import DoctorAgent
from app.core.config.settings import get_settings
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse, DoctorResponsePayload
from app.services.audio_service.audio_service import AudioService
from app.services.tts_service.tts_service import TTSService


class ChatController:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.conversation_repository = ConversationRepository()
        self.message_repository = MessageRepository()
        self.audio_service = AudioService()
        self.tts_service = TTSService()
        self.doctor_agent = DoctorAgent()

    async def send_message(
        self,
        user_id: str,
        payload: ChatMessageRequest,
    ) -> ChatMessageResponse:
        conversation_id = (
            payload.conversation_id
            if payload.conversation_id
            else self.conversation_repository.create_conversation(user_id)
        )
        user_message_id = self.message_repository.create_message(
            conversation_id=conversation_id,
            role="user",
            text=payload.text,
        )

        doctor_response = await self.doctor_agent.generate_response(payload.text)
        audio_response_url = None
        if payload.generate_audio and self.settings.enable_tts:
            tts_audio = await self.tts_service.synthesize(
                "\n".join(
                    [
                        doctor_response["summary_of_symptoms"],
                        *doctor_response["immediate_advice"],
                        doctor_response["medical_disclaimer"],
                    ]
                )
            )
            audio_response_url = self.audio_service.upload_generated_audio(
                user_id,
                tts_audio,
            )

        ai_message_id = self.message_repository.create_message(
            conversation_id=conversation_id,
            role="assistant",
            text=doctor_response["summary_of_symptoms"],
            audio_url=audio_response_url,
        )
        self.message_repository.create_ai_response(
            message_id=ai_message_id,
            response_json=doctor_response,
            audio_response_url=audio_response_url,
        )

        return ChatMessageResponse(
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            ai_message_id=ai_message_id,
            response=DoctorResponsePayload.model_validate(doctor_response),
            audio_response_url=audio_response_url,
        )
