from fastapi import APIRouter, HTTPException, Query

from app.moderation_warning_service import ModerationWarningService
from app.moderation_thread_evaluation_endpoint import (
    evaluate_thread_from_api as run_thread_evaluation,
)

router = APIRouter()

# Live-Default: feste 5-Minuten-Fenster, 5 frühere Fenster als Rolling-Historie.
warning_service = ModerationWarningService(
    window_minutes=5,
    rolling_window_size=5,
    min_history=3,
)


@router.get("/")
def read_root():
    return {"message": "Moderation Service is running"}


@router.post("/moderation/comment")
def receive_comment(comment: dict):
    return warning_service.process_comment(comment)


@router.post("/moderation/warning")
def receive_live_warning_request(payload: dict):
    try:
        return warning_service.process_warning_payload(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



def _build_counter_speech_discussion(previous_comments: list[dict]) -> str:
    lines = []
    for comment in previous_comments:
        text = str(comment.get("text", "")).strip()
        if not text:
            continue
        login = str(comment.get("login", "Nutzer")).strip() or "Nutzer"
        created_at = str(comment.get("created_at", "")).strip()
        prefix = f"{created_at} | {login}" if created_at else login
        lines.append(f"- {prefix}: {text}")
    return "\n".join(lines)


@router.post("/moderation/counter-speech/test")
def test_counter_speech_generator(payload: dict):
    """Test-Endpunkt für den Counter-Speech-Generator.

    Erwartetes Minimalformat:
    {
      "thread_context": "optional: Ausgangskommentar oder Thema",
      "previous_comments": [
        {
          "comment_id": "...",
          "parent_id": "...",
          "login": "...",
          "created_at": "...",
          "text": "..."
        }
      ]
    }

    Optional können `model_name` und `prompt_template` überschrieben werden.
    """
    previous_comments = payload.get("previous_comments")
    if not isinstance(previous_comments, list) or not previous_comments:
        raise HTTPException(
            status_code=422,
            detail="previous_comments muss eine nicht-leere Liste sein.",
        )

    discussion_text = _build_counter_speech_discussion(previous_comments)
    if not discussion_text:
        raise HTTPException(
            status_code=422,
            detail="Mindestens ein Eintrag in previous_comments muss ein nicht-leeres text-Feld enthalten.",
        )

    thread_context = (
        payload.get("thread_context")
        or payload.get("parent_text")
        or payload.get("root_text")
        or "Kein zusätzlicher Thread-Kontext übergeben."
    )

    try:
        generated_text = warning_service.counter_speech_generator.generate(
            model_name=payload.get("model_name"),
            prompt_template=payload.get("prompt_template"),
            thread_context=str(thread_context),
            diskussions_verlauf=discussion_text,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Counter-Speech-Generator konnte nicht ausgeführt werden.",
                "error": str(exc),
            },
        ) from exc

    return {
        "status": "success",
        "endpoint": "/moderation/counter-speech/test",
        "model_name": payload.get("model_name") or warning_service.counter_speech_generator.model_name,
        "previous_comments_count": len(previous_comments),
        "discussion_text": discussion_text,
        "generated_text": generated_text,
    }


@router.get("/moderation/evaluate-thread/{thread_id}")
def evaluate_thread_route(
    thread_id: str,
    platform: str = Query(..., description="bluesky oder professor"),
    source_file: str | None = Query(default=None),
    window_minutes: int = Query(
        default=5,
        ge=1,
        le=1440,
        description="Größe der Aggregationsfenster in Minuten. Default: 5.",
    ),
    rolling_window_size: int | None = Query(
        default=None,
        ge=1,
        le=500,
        description="Anzahl früherer Fenster für Rolling-z und CUSUM. Default: 5.",
    ),
    history_window_size: int | None = Query(
        default=None,
        ge=1,
        le=500,
        description="Alias für rolling_window_size, falls du den alten Parameternamen nutzen willst.",
    ),
    min_history: int = Query(
        default=3,
        ge=1,
        le=500,
        description="Mindestanzahl früherer Fenster, bevor Rolling-z/CUSUM relativ bewertet. Default: 3.",
    ),
    z_watch: float = Query(default=1.0, gt=0.0, description="z-Schwelle, ab der Evidenz beginnt."),
    z_full: float = Query(default=3.0, gt=0.0, description="z-Schwelle für volle z-Evidenz."),
    cusum_reference: float = Query(default=0.5, ge=0.0, description="CUSUM-Referenzwert k."),
    cusum_watch: float = Query(default=1.5, ge=0.0, description="CUSUM-Schwelle, ab der Evidenz beginnt."),
    cusum_full: float = Query(default=5.0, gt=0.0, description="CUSUM-Schwelle für volle Evidenz."),
    watch_threshold: float = Query(default=0.20, ge=0.0, le=1.0, description="Barometer-Schwelle für Watch."),
    warning_threshold: float = Query(default=0.40, ge=0.0, le=1.0, description="Barometer-Schwelle für Warning."),
    critical_threshold: float = Query(default=0.60, ge=0.0, le=1.0, description="Barometer-Schwelle für Critical."),
    core_watch_threshold: float = Query(default=0.20, ge=0.0, le=1.0, description="Mindestwert für Kernbedingung ab Watch."),
    core_warning_threshold: float = Query(default=0.40, ge=0.0, le=1.0, description="Mindestwert für starken Kern ab Warning/Critical."),
    support_threshold: float = Query(default=0.20, ge=0.0, le=1.0, description="Mindestwert für unterstützende Dimensionen Dynamik/Fokus."),
):
    resolved_rolling_window_size = (
        rolling_window_size
        if rolling_window_size is not None
        else history_window_size
        if history_window_size is not None
        else 5
    )

    if min_history > resolved_rolling_window_size:
        raise HTTPException(
            status_code=422,
            detail="min_history darf nicht größer als rolling_window_size/history_window_size sein.",
        )
    if z_full <= z_watch:
        raise HTTPException(status_code=422, detail="z_full muss größer als z_watch sein.")
    if cusum_full <= cusum_watch:
        raise HTTPException(status_code=422, detail="cusum_full muss größer als cusum_watch sein.")
    if not (watch_threshold <= warning_threshold <= critical_threshold):
        raise HTTPException(
            status_code=422,
            detail="Erwartet: watch_threshold <= warning_threshold <= critical_threshold.",
        )
    if core_warning_threshold < core_watch_threshold:
        raise HTTPException(
            status_code=422,
            detail="core_warning_threshold muss >= core_watch_threshold sein.",
        )

    return run_thread_evaluation(
        thread_id=thread_id,
        platform=platform,
        source_file=source_file,
        window_minutes=window_minutes,
        rolling_window_size=resolved_rolling_window_size,
        min_history=min_history,
        z_watch=z_watch,
        z_full=z_full,
        cusum_reference=cusum_reference,
        cusum_watch=cusum_watch,
        cusum_full=cusum_full,
        watch_threshold=watch_threshold,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
        
    )
