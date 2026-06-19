from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncio

import httpx

from .services.ingestion_service import start_bluesky_stream
from .timed_ingest import ingest_post
from .repositories.bluesky_repository import (
    get_threads,
    get_comments_by_thread,
)

router = APIRouter()


@router.get("/")
def read_root():
    return {"message": "Ingestion API is running"}


@router.get("/stream")
async def stream_bluesky(url: str):
    asyncio.create_task(start_bluesky_stream(url))

    return {
        "status": "stream started",
        "url": url,
    }


class IngestPostRequest(BaseModel):
    url: str
    stream_seconds: int = 30


# Bounded, awaitable ingestion used by the analysis pipeline: saves the post
# snapshot, streams new comments for stream_seconds, then returns counts.
@router.post("/ingest/post")
async def ingest_post_endpoint(body: IngestPostRequest):
    try:
        return await ingest_post(body.url, body.stream_seconds)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        # Bluesky rejected the request (e.g. post does not exist or the handle
        # does not match the post id in the URL).
        raise HTTPException(
            status_code=400,
            detail=(
                f"Bluesky API returned {exc.response.status_code} for this post. "
                "Check that the profile handle and post id in the URL belong to "
                "the same post."
            ),
        )


@router.get("/threads")
async def list_threads_from_MongoDB():
    return await get_threads()


@router.get("/threads/{thread_id}/comments")
async def list_comments_from_MongoDB(thread_id: str):
    return await get_comments_by_thread(thread_id)