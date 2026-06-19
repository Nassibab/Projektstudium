"""
timed_ingest.py
---------------
Bounded Bluesky ingestion for the analysis pipeline.

Unlike run_stream() (which listens forever), ingest_post() fetches the post
snapshot, then streams new comments for a fixed number of seconds and returns.
This makes it awaitable from POST /pipeline/bluesky/run.
"""

import asyncio
import logging

from .bluesky_live import (
    Comment,
    Link,
    PLATFORM,
    Post,
    check_link_type,
    extract_post_info,
    fetch_existing_comments,
    fetch_post_text,
    stream_post_comments,
)
from .repositories.bluesky_repository import save_comment, save_post

logger = logging.getLogger("timed_ingest")


async def ingest_post(url: str, stream_seconds: int = 30) -> dict:
    url = (url or "").strip()
    if not url:
        raise ValueError("URL is required")

    if check_link_type(url) != Link.POST:
        raise ValueError("Only Bluesky post URLs are supported for ingestion")

    handle, post_id = extract_post_info(url)

    post_text = await fetch_post_text(handle, post_id)
    existing_comments = await fetch_existing_comments(handle, post_id)

    post = Post(
        id=post_id,
        platform=PLATFORM,
        text=post_text,
        comments=existing_comments,
    )
    await save_post(post)

    initial_count = len(existing_comments)
    seen_ids = {c.id for c in existing_comments}
    streamed_count = 0

    local_queue: "asyncio.Queue[Comment]" = asyncio.Queue()

    async def consume():
        nonlocal streamed_count
        while True:
            comment = await local_queue.get()
            if comment.id not in seen_ids:
                seen_ids.add(comment.id)
                streamed_count += 1
                await save_comment(comment, post_id)
            local_queue.task_done()

    producer = asyncio.create_task(
        stream_post_comments(post_id, out_queue=local_queue)
    )
    consumer = asyncio.create_task(consume())

    logger.info("Ingest started for %s (%ss window)", post_id, stream_seconds)
    try:
        await asyncio.sleep(stream_seconds)
    finally:
        producer.cancel()
        consumer.cancel()
        await asyncio.gather(producer, consumer, return_exceptions=True)

    logger.info(
        "Ingest done for %s: %s initial, %s streamed",
        post_id,
        initial_count,
        streamed_count,
    )

    return {
        "thread_id": post_id,
        "initial_comments": initial_count,
        "streamed_comments": streamed_count,
        "total_comments": initial_count + streamed_count,
        "stream_seconds": stream_seconds,
    }
