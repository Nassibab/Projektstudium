import os

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

API_URL = os.getenv("API_URL", "http://api:8000")
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://llm-service:8011")


@router.get("/")
def read_root():
    return {"message": "Analyse-py Service is running"}


@router.post("/analyze/thread/{thread_id}")
def analyze_thread(
    thread_id: str,
    comment_ids: str | None = Query(
        default=None,
        description="Optional comma-separated comment_ids to restrict the subset.",
    ),
):
    params = {"comment_ids": comment_ids} if comment_ids else None

    try:
        with httpx.Client(timeout=120.0) as client:
            api_response = client.get(
                f"{API_URL}/threads/{thread_id}/comments/for-analysis",
                params=params,
            )
            api_response.raise_for_status()
            comments = api_response.json()

            llm_response = client.post(
                f"{LLM_SERVICE_URL}/analyze/thread",
                json={"thread_id": thread_id, "comments": comments},
            )
            llm_response.raise_for_status()
            return llm_response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {exc}")
