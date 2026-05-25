from fastapi import APIRouter

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
    return await start_bluesky_stream(url)


@router.get("/threads")
async def list_threads():
    return await get_threads()


@router.get("/threads/{thread_id}/comments")
async def list_comments(thread_id: str):
    return await get_comments_by_thread(thread_id)