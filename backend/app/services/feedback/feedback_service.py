import logging
import uuid

from postgrest.exceptions import APIError

from app.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# PostgreSQL unique_violation error code
_UNIQUE_VIOLATION = "23505"


class FeedbackService:
    def submit_feedback(
        self,
        ai_response_id: str,
        user_id: str,
        rating: int,
        comment: str | None = None,
    ) -> str:
        """Persist feedback to the response_feedback table.

        Returns the feedback id on success, or an error message string
        prefixed with "error:" on failure.
        """
        if rating not in (1, -1):
            return "error: rating must be 1 or -1"

        try:
            client = get_supabase_client()
            feedback_id = str(uuid.uuid4())
            row = {
                "id": feedback_id,
                "ai_response_id": ai_response_id,
                "user_id": user_id,
                "rating": rating,
                "comment": comment,
            }
            client.schema("before_doctor").table("response_feedback").insert(
                row
            ).execute()
            return feedback_id
        except APIError as exc:
            if _UNIQUE_VIOLATION in str(exc):
                logger.info(
                    "Duplicate feedback from user %s for response %s",
                    user_id,
                    ai_response_id,
                )
                return "error: feedback already submitted for this response"
            logger.exception(
                "Failed to submit feedback for user %s, response %s",
                user_id,
                ai_response_id,
            )
            return f"error: {exc}"
        except Exception as exc:
            logger.exception(
                "Unexpected error submitting feedback for user %s, response %s",
                user_id,
                ai_response_id,
            )
            return f"error: {exc}"
