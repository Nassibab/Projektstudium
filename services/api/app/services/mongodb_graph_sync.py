from datetime import datetime, timezone

from app.db.mongo import MongoDB
from app.repositories.data import (
    get_all_threads,
    get_all_comments_grouped_by_thread,
)
from app.repositories.graph import save_thread_with_comments


mongo = MongoDB()
threads_collection = mongo.collection("threads")


def sync_all_threads_to_graph():
    synced_threads = 0
    processed_comments = 0
    unique_comment_ids = set()

    threads = get_all_threads()
    comments_by_thread = get_all_comments_grouped_by_thread()

    for thread in threads:
        source_file = thread.get("source_file") or thread.get(
            "source_platform",
            "unknown_source",
        )
        source_platform = thread.get("source_platform")
        thread_id = thread["thread_id"]

        key = (source_file, thread_id)
        comments = comments_by_thread.get(key, [])

        print("SYNC THREAD:", key, "COMMENTS:", len(comments))

        save_thread_with_comments(thread, comments)

        threads_collection.update_one(
            {
                "thread_id": thread_id,
                "source_platform": source_platform,
            },
            {
                "$set": {
                    "synced_to_neo4j": True,
                    "synced_to_neo4j_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

        synced_threads += 1
        processed_comments += len(comments)

        for comment in comments:
            comment_id = (
                comment.get("comment_id")
                or comment.get("message_id")
                or comment.get("_id")
            )

            if comment_id:
                unique_comment_ids.add(str(comment_id))

    return {
        "status": "success",
        "synced_threads": synced_threads,
        "processed_comments": processed_comments,
        "unique_comments": len(unique_comment_ids),
    }