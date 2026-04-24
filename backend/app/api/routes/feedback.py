from fastapi import APIRouter, HTTPException, status

from app.core.security.auth import CurrentUserId
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.services.feedback.feedback_service import FeedbackService

router = APIRouter(prefix="/feedback", tags=["feedback"])
feedback_service = FeedbackService()


@router.post("", response_model=FeedbackResponse)
def submit_feedback(
    payload: FeedbackRequest,
    user_id: str = CurrentUserId,
) -> FeedbackResponse:
    if payload.rating not in (1, -1):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="rating must be 1 or -1",
        )

    result = feedback_service.submit_feedback(
        ai_response_id=payload.ai_response_id,
        user_id=user_id,
        rating=payload.rating,
        comment=payload.comment,
    )

    if result.startswith("error:"):
        error_msg = result.removeprefix("error:").strip()
        if "already submitted" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        )

    return FeedbackResponse(
        success=True,
        feedback_id=result,
        message="Feedback submitted successfully",
    )
