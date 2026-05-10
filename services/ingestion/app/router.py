from fastapi import APIRouter
from .bluesky_live import run_stream
import asyncio

router = APIRouter()

@router.get("/")
def read_root():
    return {"message": "Ingestion API is running"}

@router.get("/stream")
async def start_stream(url: str):
    asyncio.create_task(run_stream(url))
    return {"status": "streaming started", "url": url}