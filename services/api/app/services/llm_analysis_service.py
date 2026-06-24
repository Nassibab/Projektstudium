import requests
from app.database_services.mongo_data_service import (
    get_thread_comments_for_llm,
    get_thread_keys_for_llm_by_platform,
    save_llm_analysis_results_per_comment,
)

BATCH_SIZE = 50
LLM_ANALYZE_URL = "http://llm-service:8011/analyze/thread"


# ------------------------------------------------------------------------------
# Analysiert genau einen Thread mit dem LLM-Service.
#
# Diese Funktion ist die gemeinsame Basis für Professor und Bluesky.
# Sie:
# 1. Holt alle noch nicht analysierten Kommentare eines Threads.
# 2. Schickt sie batchweise an den LLM-Service.
# 3. Speichert die LLM-Features in llm_analysis_results.
# ------------------------------------------------------------------------------
def analyze_one_thread_with_llm(thread: dict) -> dict:
    thread_id = thread.get("thread_id")
    source_file = thread.get("source_file")

    if not thread_id or not source_file:
        return {"threads": 0, "comments": 0, "results": 0, "inserted": 0}

    comments = get_thread_comments_for_llm(
        thread_id=thread_id,
        source_file=source_file,
    )

    if not comments:
        return {"threads": 0, "comments": 0, "results": 0, "inserted": 0}

    total_results = 0
    total_inserted = 0

    for start in range(0, len(comments), BATCH_SIZE):
        batch = comments[start:start + BATCH_SIZE]

        response = requests.post(
            LLM_ANALYZE_URL,
            json={
                "thread_id": thread_id,
                "comments": batch,
                "temperature": 0.7,
            },
            timeout=300,
        )

        response.raise_for_status()

        batch_results = response.json().get("results", [])

        total_inserted += save_llm_analysis_results_per_comment(
            thread_id=thread_id,
            source_file=source_file,
            results=batch_results,
        )

        total_results += len(batch_results)

    return {
        "threads": 1,
        "comments": len(comments),
        "results": total_results,
        "inserted": total_inserted,
    }


# ------------------------------------------------------------------------------
# Analysiert alle noch nicht analysierten Kommentare einer bestimmten Plattform.
# Beispiele:
# - "professor_dataset"
# - "bluesky"
# ------------------------------------------------------------------------------
def analyze_platform_with_llm_service(source_platform: str) -> dict:
    threads = get_thread_keys_for_llm_by_platform(source_platform)

    total_threads = 0
    total_comments = 0
    total_results = 0
    total_inserted = 0

    for thread in threads:
        result = analyze_one_thread_with_llm(thread)

        total_threads += result["threads"]
        total_comments += result["comments"]
        total_results += result["results"]
        total_inserted += result["inserted"]

    return {
        "status": "success",
        "source_platform": source_platform,
        "batch_size": BATCH_SIZE,
        "threads_processed": total_threads,
        "comments_processed": total_comments,
        "results_count": total_results,
        "inserted_count": total_inserted,
    }


# ------------------------------------------------------------------------------
# Erzeugt LLM-Features für Professor-Daten.
# ------------------------------------------------------------------------------
def analyze_professor_with_llm_service() -> dict:
    return analyze_platform_with_llm_service("professor_dataset")


# ------------------------------------------------------------------------------
# Erzeugt LLM-Features für Bluesky-Daten.
# ------------------------------------------------------------------------------
def analyze_bluesky_with_llm_service() -> dict:
    return analyze_platform_with_llm_service("bluesky")




def analyze_one_comment_with_llm(
    *,
    thread_id: str,
    source_file: str,
    comment_id: str,
) -> dict:
    comments = get_thread_comments_for_llm(
        thread_id=thread_id,
        source_file=source_file,
        comment_ids=[comment_id],
    )

    if not comments:
        return {
            "threads": 0,
            "comments": 0,
            "results": 0,
            "inserted": 0,
            "message": "Comment not found or already analyzed",
        }

    response = requests.post(
        LLM_ANALYZE_URL,
        json={
            "thread_id": thread_id,
            "comments": comments,
            "temperature": 0.7,
        },
        timeout=300,
    )
    

    response.raise_for_status()

    results = response.json().get("results", [])

    inserted = save_llm_analysis_results_per_comment(
        thread_id=thread_id,
        source_file=source_file,
        results=results,
    )

    return {
        "threads": 1,
        "comments": len(comments),
        "results": len(results),
        "inserted": inserted,
    }


def analyze_one_bluesky_comment_with_llm_service(
    thread_id: str,
    comment_id: str,
) -> dict:
    return analyze_one_comment_with_llm(
        thread_id=thread_id,
        source_file="bluesky",
        comment_id=comment_id,
    )