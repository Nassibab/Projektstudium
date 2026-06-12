import asyncio
from ..bluesky_live import run_stream


async def start_bluesky_stream(url: str):
    asyncio.create_task(run_stream(url))
    return {
        "status": "streaming started",
        "url": url,
    }