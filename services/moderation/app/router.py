from fastapi import APIRouter, Query
#from app.services.moderate import moderate

from app.moderation_warning_service import ModerationWarningService
from app.moderation_thread_evaluation_endpoint import (
    evaluate_thread_from_api as run_thread_evaluation,
)

router = APIRouter()

warning_service = ModerationWarningService(
    window_minutes=5,
    history_window_size=3
)

@router.get("/")
def read_root():
    return {"message": "Moderation Service is running"}


@router.post("/moderation/warning")
def receive_comment(comment: dict):
    return warning_service.process_comment(comment)


@router.get("/moderation/evaluate-thread/{thread_id}")
def evaluate_thread_route(
    thread_id: str,
    platform: str = Query(..., description="bluesky oder professor"),
    source_file: str | None = Query(default=None),
):
    return run_thread_evaluation(
        thread_id=thread_id,
        platform=platform,
        source_file=source_file,
    )