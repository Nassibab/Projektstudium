import json
import requests
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.database_services.mongo_data_service import (
    get_all_comments_for_analysis,
    get_bluesky_comments_for_prediction,
    save_analysis_results,
)
from app.db.mongo import MongoDB
from app.importers.professor_json_importer import import_json
from app.importers.professor_llm_json_importer import import_professor_llm_dataset
from app.services.llm_analysis_service import (
    analyze_bluesky_with_llm_service,
    analyze_professor_with_llm_service,
)
from app.services.mongodb_graph_sync import (
    reset_mongo_sync_status_if_missing_in_neo4j,
    sync_all_threads_to_graph,
)
from app.services.redis_events import (
    iter_thread_updates, 
    publish_thread_update, 
    set_cached_threads, 
    get_cached_threads
)
from app.services.report_service import get_thread_report

router = APIRouter()

try:
    mongo_db = MongoDB()
    comments_collection = mongo_db.collection("comments")
except Exception as e:
    print(f"Warnung: MongoDB konnte beim Start nicht verbunden werden: {e}")
    comments_collection = None


def _get_frontend_comment_from_moderation(comment: dict) -> dict:
    payload = dict(comment)
    if payload.get("id") is None and payload.get("comment_id") is not None:
        payload["id"] = payload["comment_id"]
    if payload.get("thread_id") is None and payload.get("threadId") is not None:
        payload["thread_id"] = payload["threadId"]

    try:
        response = requests.post("http://moderation:8000/moderate/batch", json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        if isinstance(result, dict) and isinstance(result.get("comment"), dict):
            return result["comment"]
    except Exception as exc:
        print(f"Cold-start moderation failed for comment {payload.get('id')}: {exc}")

    moderation_result = comment.get("moderation_result")
    if isinstance(moderation_result, dict):
        warning_level = moderation_result.get("warning_level", moderation_result.get("moderation", "Unbekannt"))
        if "shitstorm_barometer" in moderation_result:
            score_value = round(float(moderation_result.get("shitstorm_barometer", 0.0)) / 100, 4)
        else:
            score_value = moderation_result.get("barometer_score_0_1", moderation_result.get("score", 0.0))
        dimension_scores = moderation_result.get("dimension_scores", moderation_result.get("kpis", {}))
        kpis = [{"name": k, "value": v} for k, v in dimension_scores.items()]
        return {
            "id": comment.get("comment_id") or comment.get("id"),
            "author": comment.get("author") or comment.get("user") or "Unbekannt",
            "time": comment.get("created_at") or comment.get("time") or comment.get("timestamp"),
            "text": comment.get("text", ""),
            "moderation": warning_level,
            "score": score_value,
            "kpis": kpis,
            "countermeasures": {},
            "counter_speech": {"should_generate": False, "generated_text": None},
        }

    return {
        "id": payload.get("id") or payload.get("comment_id"),
        "author": payload.get("author") or payload.get("user") or "Unbekannt",
        "time": payload.get("created_at") or payload.get("time") or payload.get("timestamp"),
        "text": payload.get("text", ""),
        "moderation": "Unbekannt",
        "score": 0.0,
        "kpis": [],
        "countermeasures": {},
        "counter_speech": {"should_generate": False, "generated_text": None},
    }


def warmup_redis_cache():
    if comments_collection is None:
        return

    print("Lade die neuesten 2 Threads aus MongoDB in den Redis-Cache...")
    
    # 1. Hole die letzten 2 Threads
    latest_threads_cursor = mongo_db.collection("threads").find({}, {"_id": 0}).sort("_id", -1).limit(2)
    latest_threads = list(latest_threads_cursor)
    result = []

    for thread in latest_threads:
        thread_id = thread.get("thread_id")
        comments = list(comments_collection.find({"thread_id": thread_id}, {"_id": 0}).sort("created_at", 1))
        
        formatted_comments = []
        for c in comments:
            frontend_comment = _get_frontend_comment_from_moderation(c)

            formatted_comments.append({
                "id": frontend_comment.get("id") or c.get("comment_id") or c.get("id"),
                "author": frontend_comment.get("author") or c.get("user") or "Unbekannt",
                "time": frontend_comment.get("time") or c.get("created_at"),
                "text": frontend_comment.get("text", c.get("text", "")),
                "moderation": frontend_comment.get("moderation", "Unbekannt"),
                "score": frontend_comment.get("score", 0.0),
                "kpis": frontend_comment.get("kpis", []),
                "countermeasures": frontend_comment.get("countermeasures", {}),
                "counter_speech": frontend_comment.get("counter_speech", {"should_generate": False, "generated_text": None}),
            })
            
        result.append({
            "id": thread_id,
            "title": thread.get("title") or f"Thread {thread_id}",
            "text": thread.get("text", ""),
            "comments": formatted_comments
        })

    print("Cold-start payload for frontend from Redis:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    set_cached_threads(result)


def save_to_mongodb_background(payload: dict):
    """Speichert den aktuellen Zwischenstand (Kommentar + bisherige Scores) in der DB"""
    if comments_collection is None:
        print("Background Task: MongoDB ist nicht verbunden. Überspringe Speichern.")
        return

    comment_data = payload.get("comment", {})
    if comment_data and comment_data.get("id"):
        try:
            comments_collection.update_one(
                {"comment_id": comment_data["id"]}, 
                {"$set": comment_data}, 
                upsert=True
            )
            print(f"In MongoDB gespeichert: ID {comment_data['id']}")
        except Exception as e:
            print(f"Fehler bei MongoDB Speicherung: {e}")


def forward_to_analyse_r(payload: dict):
    """Gibt die Daten sofort an R weiter"""
    try:
        requests.post("http://analyse-r:8000/analyze-event", json=payload, timeout=10)
        print("➡️ An Analyse-R weitergeleitet")
    except Exception as e:
        print(f"Analyse-R noch nicht erreichbar (ignoriert): {e}")


def forward_to_moderation(payload: dict):
    """Gibt die Daten an die Moderation weiter"""
    try:
        requests.post("http://moderation:8000/moderate", json=payload, timeout=10)
        print("An Moderation weitergeleitet")
    except Exception as e:
        print(f"Moderation noch nicht erreichbar (ignoriert): {e}")


@router.get("/")
def read_root():
    return {"message": "API is running"}

@router.post("/import/professor")
def import_professor_data_into_MongoDB():
    import_json()
    return {
        "status": "success",
        "message": "Professor data imported"
    }

@router.post("/sync/graph")
def sync_MongoDB_NEO4J():
    return sync_all_threads_to_graph()

@router.get("/report/threads")
def report_threads_in_MongoDB_and_NEO4J():
    return get_thread_report()

@router.post("/sync/reset-missing-neo4j")
def reset_missing_neo4j_sync_status():
    return reset_mongo_sync_status_if_missing_in_neo4j()

@router.get("/analysis/comments")
def get_analysis_comments():
    return get_all_comments_for_analysis()

@router.get("/events/stream")
def stream_demo_updates():
    return StreamingResponse(iter_thread_updates(), media_type="text/event-stream")


@router.post("/events/llm-labeled")
def event_llm_labeled(payload: dict, background_tasks: BackgroundTasks):
    """SCHRITT 1: Wird vom LLM aufgerufen, sobald Labels fertig sind."""
    publish_thread_update(payload)
    background_tasks.add_task(save_to_mongodb_background, payload)
    background_tasks.add_task(forward_to_analyse_r, payload)

    return {"status": "ok", "message": "Broadcasted to UI, DB, and R"}


@router.post("/events/analysis-completed")
def event_analysis_completed(payload: dict, background_tasks: BackgroundTasks):
    """SCHRITT 2: Wird von R (analyse-r) aufgerufen, sobald Scores berechnet sind."""
    publish_thread_update(payload)
    background_tasks.add_task(save_to_mongodb_background, payload)
    background_tasks.add_task(forward_to_moderation, payload)

    return {"status": "ok", "message": "Broadcasted to UI, DB, and Moderation"}


@router.post("/events/save-moderation")
def save_moderation_result(payload: dict):
    print("Neue Moderationsergebnisse erhalten:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if comments_collection is not None:
        comments_collection.update_one(
            {"comment_id": payload.get("comment_id")}, 
            {"$set": {
                "moderation_result": payload.get("moderation_result"),
                "score": payload.get("score"),
                "kpis": payload.get("kpis")
            }}, 
            upsert=True
        )
    return {"status": "saved"}


@router.get("/threads/latest")
def get_latest_threads():
    cached_data = get_cached_threads()
    
    if cached_data is None:
        print("Redis Cache existiert noch nicht! Führe manuelles Cache-Warmup mit DB-Daten durch...")
        warmup_redis_cache()
        cached_data = get_cached_threads()

    print("Payload returned to frontend from Redis:")
    print(json.dumps(cached_data if cached_data is not None else [], ensure_ascii=False, indent=2))
    
    return cached_data if cached_data is not None else []