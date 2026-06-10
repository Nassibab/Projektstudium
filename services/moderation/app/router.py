from fastapi import APIRouter
#from app.services.moderate import moderate

from app.warning_services.moderation_warning_service import ModerationWarningService

router = APIRouter()

warning_service = ModerationWarningService(
    window_minutes=5,
    history_window_size=3
)

@router.get("/")
def read_root():
    return {"message": "Moderation Service is running"}


#@router.post("/moderate")
#async def moderate_endpoint(payload: dict):
   # return await moderate(payload)


@router.post("/moderation/warning")
def receive_comment(comment: dict):
    return warning_service.process_comment(comment)
