import json
from fastapi import APIRouter
import requests
from app.moderation_warning_service import ModerationWarningService

router = APIRouter()

warning_service = ModerationWarningService(
    window_minutes=5,
    history_window_size=3
)

@router.get("/")
def read_root():
    return {"message": "Moderation Service is running"}


@router.post("/moderate")
def receive_comment_compat(payload: dict):
    print("Neue Moderationsanfrage erhalten:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    # Moderation durchführen
    result = warning_service.process_comment(payload)
    
    # Rückmeldung an die API zum Speichern in MongoDB
    try:
        # Wir schicken das Ergebnis an den neuen Endpunkt in der API
        requests.post("http://api:8000/events/save-moderation", json={
            "comment_id": payload.get("id"),
            "moderation_result": result,
            "score": result.get("barometer_score_0_1"),
            "kpis": result.get("dimension_scores")
        })
    except Exception as e:
        print(f"API für Speicherung nicht erreichbar: {e}")
        
    return result


@router.post("/moderation/warning")
def receive_comment(comment: dict):
    print("Neue Moderationswarnung erhalten:")
    print(json.dumps(comment, ensure_ascii=False, indent=2))
    return warning_service.process_comment(comment)

@router.post("/moderate/batch")
def moderate_batch(payload: dict):
    print("Neue Batch-Moderationsanfrage erhalten:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return warning_service.process_comment(payload, is_batch=True)