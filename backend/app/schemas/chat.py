from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    conversation_id: str | None = None
    text: str = Field(min_length=2, max_length=4000)
    transcript_id: str | None = None
    generate_audio: bool = True


class DoctorResponsePayload(BaseModel):
    summary_of_symptoms: str
    possible_causes: list[str]
    immediate_advice: list[str]
    lifestyle_suggestions: list[str]
    warning_signs: list[str]
    when_to_see_a_real_doctor: str
    medical_disclaimer: str
    follow_up_questions: list[str]


class ChatMessageResponse(BaseModel):
    conversation_id: str
    user_message_id: str
    ai_message_id: str
    response: DoctorResponsePayload
    audio_response_url: str | None = None
