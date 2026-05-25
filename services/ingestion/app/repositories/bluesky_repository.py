import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongodb:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "shitstorm_db")

client = AsyncIOMotorClient(MONGO_URL)
db = client[MONGO_DB_NAME]

threads_collection = db["threads"]
comments_collection = db["comments"]


async def save_post(post):
    now = datetime.now(timezone.utc).isoformat()

    await threads_collection.update_one(
        {
            "thread_id": post.id,
            "source_platform": "bluesky",
        },
        {
            "$set": {
                "thread_id": post.id,
                "external_id": post.id,

                "source_provider": "external_platform",
                "source_platform": "bluesky",
                "source_type": "live",
                "source_file": None,

                "title": None,
                "root_text": post.text,
                "platform": post.platform,

                "comments_count": len(post.comments),
                "status": "raw",
                "imported_at": now,
            }
        },
        upsert=True,
    )

    for comment in post.comments:
        await save_comment(comment, post.id)


async def save_comment(comment, thread_id: str):
    now = datetime.now(timezone.utc).isoformat()

    await comments_collection.update_one(
        {
            "comment_id": comment.id,
            "source_platform": "bluesky",
        },
        {
            "$set": {
                "comment_id": comment.id,
                "message_id": comment.id,

                "thread_id": thread_id,

                "parent": comment.parent_id,
                "parent_id": comment.parent_id,

                "login": comment.author,
                "author": comment.author,

                "text": comment.text,
                "created": None,

                "source_provider": "external_platform",
                "source_platform": "bluesky",
                "source_type": "live",
                "source_file": None,

                "status": "raw",
                "imported_at": now,
            }
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
    async for comment in comments_collection.find({"thread_id": thread_id}):
        comment["_id"] = str(comment["_id"])
        comments.append(comment)
    return comments