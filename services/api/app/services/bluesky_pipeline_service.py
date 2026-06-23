import asyncio
import logging
import os
import time

from app.services.bluesky_pipeline_models import PipelineRun, PipelineStep
from app.services.llm_analysis_service import analyze_one_thread_with_llm
from app.services.redis_events import publish_thread_update
from app.database_services.mongo_data_service import (
    get_bluesky_prediction_comments,
    get_bluesky_thread_ids,
    upsert_moderation_suggestions,
)
from app.utils import http_retry

logger = logging.getLogger(__name__)

INGESTION_URL = os.getenv("INGESTION_URL", "http://ingestion:8001")
ANALYSE_R_URL = os.getenv("ANALYSE_R_URL", "http://analyse-r:8000")
MODERATION_URL = os.getenv("MODERATION_URL", "http://moderation:8000")
PIPELINE_INTERVAL_SEC = int(os.getenv("PIPELINE_INTERVAL_SEC", "1800"))

SOURCE_FILE = "bluesky"

LLM_TIMEOUT = 300
PREDICT_TIMEOUT = 600
MODERATION_TIMEOUT = 30


def _log_step(run: PipelineRun, step: PipelineStep) -> None:
    logger.info(
        "[pipeline] run_id=%s thread=%s step=%s status=%s duration_ms=%s message=%s",
        run.run_id, run.thread_id, step.name, step.status, step.duration_ms, step.message,
    )


# ------------------------------------------------------------------------------
# Step 1: LLM enrichment (in-process, reuses the existing per-thread function).
# ------------------------------------------------------------------------------
def _step_llm(thread_id: str) -> PipelineStep:
    start = time.perf_counter()
    step = PipelineStep(name="llm")

    try:
        result = analyze_one_thread_with_llm({
            "thread_id": thread_id,
            "source_file": SOURCE_FILE,
        })

        if result.get("comments", 0) == 0:
            step.status = "skipped"
            step.message = "no new comments to analyze"
        else:
            step.status = "success"
            step.message = (
                f"analyzed {result.get('comments', 0)} comments, "
                f"inserted {result.get('inserted', 0)}"
            )
    except Exception as exc:  # noqa: BLE001 - surface any failure as a failed step
        step.status = "failed"
        step.message = f"{type(exc).__name__}: {exc}"

    step.duration_ms = int((time.perf_counter() - start) * 1000)
    return step


# ------------------------------------------------------------------------------
# Step 2: R prediction. analyse-r reads the thread, predicts, and POSTs the
# results back to the API, which upserts them into the prediction collections.
# ------------------------------------------------------------------------------
def _step_predict(thread_id: str) -> PipelineStep:
    start = time.perf_counter()
    step = PipelineStep(name="predict")

    try:
        response = http_retry.get(
            f"{ANALYSE_R_URL}/predict-bluesky",
            params={"thread_id": thread_id},
            timeout=PREDICT_TIMEOUT,
        )

        if response.status_code >= 400:
            step.status = "failed"
            step.message = f"analyse-r returned {response.status_code}: {response.text[:200]}"
        else:
            body = response.json()
            step.status = "success"
            step.message = f"predicted {body.get('predicted_rows', 0)} rows"
    except Exception as exc:  # noqa: BLE001
        step.status = "failed"
        step.message = f"{type(exc).__name__}: {exc}"

    step.duration_ms = int((time.perf_counter() - start) * 1000)
    return step


# ------------------------------------------------------------------------------
# Step 3: Moderation. Reads predictions from Mongo, asks the moderation service
# for suggestions, and upserts them into moderation_suggestions.
# ------------------------------------------------------------------------------
def _step_moderate(thread_id: str) -> PipelineStep:
    start = time.perf_counter()
    step = PipelineStep(name="moderate")

    try:
        predictions = get_bluesky_prediction_comments(thread_id)

        if not predictions:
            step.status = "skipped"
            step.message = "no predictions to moderate"
            step.duration_ms = int((time.perf_counter() - start) * 1000)
            return step

        batch = [
            {
                "comment_id": p.get("comment_id"),
                "text": p.get("text"),
                "toxicity_score": p.get("toxicity_score"),
                "attack_score": p.get("attack_score"),
                "irony": p.get("irony"),
                "predicted_role": p.get("predicted_synthetic_role_label"),
            }
            for p in predictions
        ]

        response = http_retry.post(
            f"{MODERATION_URL}/suggest/batch",
            json={"comments": batch},
            timeout=MODERATION_TIMEOUT,
        )

        if response.status_code >= 400:
            step.status = "failed"
            step.message = f"moderation returned {response.status_code}: {response.text[:200]}"
        else:
            suggestions = response.json().get("suggestions", [])
            saved = upsert_moderation_suggestions(thread_id, suggestions)
            step.status = "success"
            step.message = f"saved {saved} suggestions"
    except Exception as exc:  # noqa: BLE001
        step.status = "failed"
        step.message = f"{type(exc).__name__}: {exc}"

    step.duration_ms = int((time.perf_counter() - start) * 1000)
    return step


# ------------------------------------------------------------------------------
# Step 4: Notify the frontend that this thread has fresh results (via Redis SSE).
# The frontend reloads the live data on this event, which avoids duplicating
# comments in an open dashboard session.
# ------------------------------------------------------------------------------
def _step_notify(run: PipelineRun) -> PipelineStep:
    start = time.perf_counter()
    step = PipelineStep(name="notify")

    try:
        publish_thread_update({
            "type": "thread_analyzed",
            "threadId": run.thread_id,
            "run_id": run.run_id,
        })
        step.status = "success"
    except Exception as exc:  # noqa: BLE001
        step.status = "failed"
        step.message = f"{type(exc).__name__}: {exc}"

    step.duration_ms = int((time.perf_counter() - start) * 1000)
    return step


# ------------------------------------------------------------------------------
# Full per-thread pipeline. Stops on the first failed step.
# ------------------------------------------------------------------------------
def run_bluesky_thread_pipeline(thread_id: str) -> PipelineRun:
    run = PipelineRun(thread_id=thread_id)

    for step_fn in (_step_llm, _step_predict, _step_moderate):
        step = step_fn(thread_id)
        run.add_step(step)
        _log_step(run, step)

        if step.status == "failed":
            run.finish()
            return run

    notify = _step_notify(run)
    run.add_step(notify)
    _log_step(run, notify)

    run.finish()
    return run


# ------------------------------------------------------------------------------
# Runs the pipeline for one thread (if given) or every Bluesky thread in Mongo.
# ------------------------------------------------------------------------------
def process_pending_bluesky_threads(thread_id: str | None = None) -> list[dict]:
    thread_ids = [thread_id] if thread_id else get_bluesky_thread_ids()

    runs = [run_bluesky_thread_pipeline(tid) for tid in thread_ids]
    return [run.to_dict() for run in runs]


# ------------------------------------------------------------------------------
# Starts the live Bluesky ingestion stream on the ingestion service.
# ------------------------------------------------------------------------------
def start_bluesky_ingestion(url: str) -> dict:
    response = http_retry.get(
        f"{INGESTION_URL}/stream",
        params={"url": url},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


# ------------------------------------------------------------------------------
# Background scheduler: runs the pipeline for all threads every interval.
# Sync work runs in a worker thread so it never blocks the event loop.
# ------------------------------------------------------------------------------
async def pipeline_scheduler_loop() -> None:
    while True:
        await asyncio.sleep(PIPELINE_INTERVAL_SEC)
        try:
            logger.info("[pipeline] scheduled run starting")
            await asyncio.to_thread(process_pending_bluesky_threads)
            logger.info("[pipeline] scheduled run finished")
        except Exception:  # noqa: BLE001
            logger.exception("[pipeline] scheduled run failed")


def start_pipeline_scheduler() -> None:
    asyncio.create_task(pipeline_scheduler_loop())
