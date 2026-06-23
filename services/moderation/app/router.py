import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
#from app.services.moderate import moderate

from app.moderation_warning_service import ModerationWarningService

logger = logging.getLogger(__name__)

router = APIRouter()

# Der Warning-Service initialisiert intern einen LLM-Client (OpenAI) und benötigt
# einen API-Key. Fehlt dieser, soll der Service trotzdem starten, damit die
# regelbasierte Batch-Moderation (/suggest/batch) der Bluesky-Pipeline läuft.
try:
    warning_service = ModerationWarningService(
        window_minutes=5,
        history_window_size=3
    )
except Exception as exc:  # noqa: BLE001
    warning_service = None
    logger.warning("ModerationWarningService not available: %s", exc)

@router.get("/")
def read_root():
    return {"message": "Moderation Service is running"}


#@router.post("/moderate")
#async def moderate_endpoint(payload: dict):
   # return await moderate(payload)


@router.post("/moderation/warning")
def receive_comment(comment: dict):
    if warning_service is None:
        raise HTTPException(
            status_code=503,
            detail="ModerationWarningService unavailable (missing LLM credentials).",
        )
    return warning_service.process_comment(comment)


# ------------------------------------------------------------------------------
# Batch-Moderation (MVP) für die Bluesky-Pipeline
# Normalisiert die LLM-Scores auf [0, 1], kombiniert sie und ordnet eine Stufe zu.
# ------------------------------------------------------------------------------

class CommentInput(BaseModel):
    comment_id: str | int
    text: str | None = None
    toxicity_score: float | None = None  # LLM scale 1-4
    attack_score: float | None = None    # LLM scale 1-10
    irony: float | None = None           # LLM scale 1-5
    predicted_role: str | None = None


class SuggestBatchRequest(BaseModel):
    comments: list[CommentInput] = []


ATTACK_ROLES = {"attack", "target_response"}

TIERS = {
    "Kritisch": {
        "recommended_action": "remove_and_report",
        "moderation_text": (
            "Kritisch: Sehr hohe Toxizität bzw. eindeutige Richtlinienverletzung. "
            "Beitrag sofort entfernen, User sperren und Vorfall prüfen."
        ),
    },
    "Eskalation": {
        "recommended_action": "hide_and_warn",
        "moderation_text": (
            "Eskalation: Hohe Toxizität und klare Grenzüberschreitung. "
            "Beitrag verbergen und User verwarnen."
        ),
    },
    "Frühwarnung": {
        "recommended_action": "monitor",
        "moderation_text": (
            "Frühwarnung: Der Ton wird schärfer und unsachlich. "
            "Im Auge behalten, Eskalationsgefahr."
        ),
    },
    "Unauffällig": {
        "recommended_action": "none",
        "moderation_text": "Unauffällig. Sachlicher Beitrag, keine Aktion erforderlich.",
    },
}


def _normalize(value, low: float, high: float) -> float:
    if value is None or high == low:
        return 0.0
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, (numeric - low) / (high - low)))


def _tier_for_score(score: float) -> str:
    if score >= 0.75:
        return "Kritisch"
    if score >= 0.50:
        return "Eskalation"
    if score >= 0.25:
        return "Frühwarnung"
    return "Unauffällig"


def _suggest_one(comment: CommentInput) -> dict:
    toxicity = _normalize(comment.toxicity_score, 1, 4)
    attack = _normalize(comment.attack_score, 1, 10)

    score = max(toxicity, attack)

    # Eine vom Modell erkannte Angriffsrolle erhöht die Stufe leicht.
    if comment.predicted_role in ATTACK_ROLES:
        score = min(1.0, score + 0.15)

    tier = _tier_for_score(score)
    tier_info = TIERS[tier]

    return {
        "comment_id": comment.comment_id,
        "tier": tier,
        "score": round(score, 2),
        "moderation_text": tier_info["moderation_text"],
        "recommended_action": tier_info["recommended_action"],
    }


@router.post("/suggest/batch")
def suggest_batch(payload: SuggestBatchRequest):
    suggestions = [_suggest_one(comment) for comment in payload.comments]
    return {"suggestions": suggestions}
