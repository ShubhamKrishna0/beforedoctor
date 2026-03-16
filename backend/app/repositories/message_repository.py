from uuid import uuid4

from app.database.supabase_client import get_supabase_client


class MessageRepository:
    def __init__(self) -> None:
        self.client = get_supabase_client()
        self.schema = "before_doctor"

    def create_message(
        self,
        conversation_id: str,
        role: str,
        text: str | None,
        audio_url: str | None = None,
    ) -> str:
        message_id = str(uuid4())
        self.client.schema(self.schema).table("messages").insert(
            {
                "id": message_id,
                "conversation_id": conversation_id,
                "role": role,
                "text": text,
                "audio_url": audio_url,
            }
        ).execute()
        return message_id

    def create_transcript(
        self,
        message_id: str,
        original_text: str,
        edited_text: str,
    ) -> str:
        transcript_id = str(uuid4())
        self.client.schema(self.schema).table("transcripts").insert(
            {
                "id": transcript_id,
                "message_id": message_id,
                "original_text": original_text,
                "edited_text": edited_text,
            }
        ).execute()
        return transcript_id

    def update_transcript(self, transcript_id: str, edited_text: str) -> None:
        (
            self.client.schema(self.schema)
            .table("transcripts")
            .update({"edited_text": edited_text})
            .eq("id", transcript_id)
            .execute()
        )

    def create_ai_response(
        self,
        message_id: str,
        response_json: dict,
        audio_response_url: str | None = None,
    ) -> None:
        self.client.schema(self.schema).table("ai_responses").insert(
            {
                "id": str(uuid4()),
                "message_id": message_id,
                "response_json": response_json,
                "audio_response_url": audio_response_url,
            }
        ).execute()

    def create_audio_file(
        self,
        user_id: str,
        audio_url: str,
        duration: float | None = None,
    ) -> str:
        audio_file_id = str(uuid4())
        self.client.schema(self.schema).table("audio_files").insert(
            {
                "id": audio_file_id,
                "user_id": user_id,
                "audio_url": audio_url,
                "duration": duration,
            }
        ).execute()
        return audio_file_id
