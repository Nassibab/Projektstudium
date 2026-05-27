from fastapi import APIRouter
import asyncio

from .services.ingestion_service import start_bluesky_stream
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


@router.get("/threads")
async def list_threads_from_MongoDB():
    return await get_threads()


@router.get("/threads/{thread_id}/comments")
async def list_comments_from_MongoDB(thread_id: str):
    return await get_comments_by_thread(thread_id)