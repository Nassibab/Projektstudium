import logging
import os

import requests

from app.services.llm_analysis_service import analyze_bluesky_with_llm_service

logger = logging.getLogger("bluesky_pipeline")

ANALYSE_R_URL = os.getenv("ANALYSE_R_URL", "http://analyse-r:8000")

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
def run_bluesky_analysis() -> dict:
    logger.info("Bluesky run started")

    # Step 1: LLM features
    logger.info("Step 1/2: LLM analysis...")
    llm_result = analyze_bluesky_with_llm_service()
    logger.info(
        "Step 1/2 done: %s comments, %s inserted",
        llm_result.get("comments_processed"),
        llm_result.get("inserted_count"),
    )

    # Step 2: R prediction (reads from API, predicts, posts results back)
    logger.info(
        "Step 2/2: calling analyse-r /predict-bluesky (this can take a few minutes)..."
    )
    try:
        response = requests.get(
            f"{ANALYSE_R_URL}/predict-bluesky",
            timeout=PREDICT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        predict_result = response.json()
    except requests.RequestException as exc:
        logger.exception("Bluesky run FAILED at step predict")
        return {
            "status": "error",
            "step": "predict",
            "message": str(exc),
            "llm": llm_result,
        }

    logger.info("Step 2/2 done: %s", predict_result.get("status"))
    logger.info("Bluesky run finished")

    return {
        "status": "success",
        "llm": llm_result,
        "predict": {
            "status": predict_result.get("status"),
            "predicted_rows": predict_result.get("predicted_rows"),
            "save_status": predict_result.get("save_status"),
        },
    }
