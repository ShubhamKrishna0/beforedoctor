from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    ai_response_id: str
    rating: int = Field(..., description="1 for thumbs up, -1 for thumbs down")
    comment: str | None = None


class FeedbackResponse(BaseModel):
    success: bool
    feedback_id: str | None = None
    message: str | None = None
