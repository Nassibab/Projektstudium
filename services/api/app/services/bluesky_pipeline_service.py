import logging
import os

import requests

from app.services.llm_analysis_service import (
    analyze_bluesky_with_llm_service,
    analyze_bluesky_thread_with_llm,
)

logger = logging.getLogger("bluesky_pipeline")

ANALYSE_R_URL = os.getenv("ANALYSE_R_URL", "http://analyse-r:8000")
INGESTION_URL = os.getenv("INGESTION_URL", "http://ingestion:8001")

# R prediction loads a model and processes the whole thread, so it can take a
# few minutes. Keep the timeout generous so a slow run is not mistaken for a hang.
PREDICT_TIMEOUT_SECONDS = 600


# ------------------------------------------------------------------------------
# Verbindet Ingestion und Analyse über einen einzigen manuellen Aufruf.
#
# Ingestion und Analyse sind über die Datenbank entkoppelt. Diese Funktion ist
# nur eine Bequemlichkeit, die die zwei bereits existierenden Schritte in einem
# Aufruf nacheinander ausführt:
#   1. LLM-Features für Bluesky erzeugen (in-process).
#   2. analyse-r /predict-bluesky aufrufen (R liest Daten, predicted und
#      speichert die Ergebnisse selbst über /analysis/save-results zurück).
# ------------------------------------------------------------------------------
def run_bluesky_analysis(
    thread_id: str | None = None,
    url: str | None = None,
    stream_seconds: int = 30,
) -> dict:
    scope = f"thread_id={thread_id}" if thread_id else "all threads"
    logger.info("Bluesky run started (%s)", scope)

    # Step 0: Ingest a post URL (snapshot + timed live stream). When a url is
    # given, the ingested post's thread_id drives the rest of the pipeline.
    ingest_result = None
    if url:
        logger.info("Step 0: ingesting %s (%ss stream)...", url, stream_seconds)
        try:
            response = requests.post(
                f"{INGESTION_URL}/ingest/post",
                json={"url": url, "stream_seconds": stream_seconds},
                timeout=stream_seconds + 60,
            )
            response.raise_for_status()
            ingest_result = response.json()
        except requests.RequestException as exc:
            logger.exception("Bluesky run FAILED at step ingest")
            return {
                "status": "error",
                "step": "ingest",
                "message": str(exc),
            }

        thread_id = ingest_result.get("thread_id")
        logger.info(
            "Step 0 done: %s initial, %s streamed (thread_id=%s)",
            ingest_result.get("initial_comments"),
            ingest_result.get("streamed_comments"),
            thread_id,
        )

    # Step 1: LLM features (one thread, or all bluesky threads)
    logger.info("Step 1/2: LLM analysis...")
    if thread_id:
        llm_result = analyze_bluesky_thread_with_llm(thread_id)
    else:
        llm_result = analyze_bluesky_with_llm_service()

    if llm_result.get("status") == "error":
        logger.error("Bluesky run FAILED at step llm: %s", llm_result.get("message"))
        return {
            "status": "error",
            "step": "llm",
            "message": llm_result.get("message"),
            "ingest": ingest_result,
            "llm": llm_result,
        }

    logger.info(
        "Step 1/2 done: %s comments, %s inserted",
        llm_result.get("comments_processed"),
        llm_result.get("inserted_count"),
    )

    # Step 2: R prediction (reads from API, predicts, posts results back)
    logger.info(
        "Step 2/2: calling analyse-r /predict-bluesky (this can take a few minutes)..."
    )
    url = f"{ANALYSE_R_URL}/predict-bluesky"
    if thread_id:
        url += f"?thread_id={thread_id}"
    try:
        response = requests.get(url, timeout=PREDICT_TIMEOUT_SECONDS)
        response.raise_for_status()
        predict_result = response.json()
    except requests.RequestException as exc:
        logger.exception("Bluesky run FAILED at step predict")
        return {
            "status": "error",
            "step": "predict",
            "message": str(exc),
            "ingest": ingest_result,
            "llm": llm_result,
        }

    logger.info("Step 2/2 done: %s", predict_result.get("status"))
    logger.info("Bluesky run finished")

    return {
        "status": "success",
        "thread_id": thread_id,
        "ingest": ingest_result,
        "llm": llm_result,
        "predict": {
            "status": predict_result.get("status"),
            "predicted_rows": predict_result.get("predicted_rows"),
            "save_status": predict_result.get("save_status"),
        },
    }
