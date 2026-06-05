import os
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

from app.mappers.comment_mapper import map_comment
from app.mappers.thread_mapper import map_thread


MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongodb:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "shitstorm_db")

client = AsyncIOMotorClient(MONGO_URL)
db = client[MONGO_DB_NAME]

threads_collection = db["threads"]
comments_collection = db["comments"]


async def save_post(post):
    now = datetime.now(timezone.utc).isoformat()

    mapped_thread = map_thread(
        thread_id=post.id,
        title=post.text,
        comments_count=len(post.comments),
        source_platform="bluesky",
        source_type="prediction_data",
    )

    await threads_collection.update_one(
        {
            "thread_id": post.id,
            "source_platform": "bluesky",
        },
        {
            "$set": mapped_thread
        },
        upsert=True,
    )

    for comment in post.comments:
        await save_comment(comment, post.id)


async def save_comment(comment, thread_id: str):
    mapped_comment = map_comment(
        comment_id=comment.id,
        thread_id=thread_id,
        user=comment.author,
        text=comment.text,
        parent_id=comment.parent_id,
        created_at=comment.created_at,
        source_platform="bluesky",
        source_type="prediction_data",
    )

    await comments_collection.update_one(
        {
            "comment_id": comment.id,
            "source_platform": "bluesky",
        },
        {
            "$set": mapped_comment
        },
        upsert=True,
    )


async def get_threads():
    threads = []

    async for thread in threads_collection.find({}):
        thread["_id"] = str(thread["_id"])
        threads.append(thread)

    return threads


async def get_comments_by_thread(thread_id: str):
    comments = []

    async for comment in comments_collection.find(
        {
            "thread_id": thread_id,
            "source_platform": "bluesky",
        }
    ):
        comment["_id"] = str(comment["_id"])
        comments.append(comment)

    return comments