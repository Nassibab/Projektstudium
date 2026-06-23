from datetime import datetime, timezone

from app.db.mongo import MongoDB
from app.db.neo4j import get_driver
from app.database_services.mongo_data_service import (
    get_all_threads,
    get_all_comments_grouped_by_thread,
)
from app.database_services.graph_data_service import save_thread_with_comments


mongo = MongoDB()
threads_collection = mongo.collection("threads")


def build_graph_thread_id(thread: dict) -> str:
    source_platform = thread.get("source_platform", "unknown")
    source_type = thread.get("source_type", "unknown")
    thread_id = thread["thread_id"]

    return f"{source_platform}:{source_type}:{thread_id}"


def thread_exists_in_neo4j(thread: dict) -> bool:
    graph_thread_id = build_graph_thread_id(thread)
    driver = get_driver()

    with driver.session() as session:
        result = session.run(
            """
            MATCH (t:Thread {id: $graph_thread_id})
            RETURN t
            LIMIT 1
            """,
            graph_thread_id=graph_thread_id,
        )

        return result.single() is not None


def reset_mongo_sync_status_if_missing_in_neo4j():
    threads = list(
        threads_collection.find({
            "synced_to_neo4j": True
        })
    )

    reset_count = 0

    for thread in threads:
        if not thread_exists_in_neo4j(thread):
            threads_collection.update_one(
                {"_id": thread["_id"]},
                {
                    "$unset": {
                        "synced_to_neo4j": "",
                        "synced_to_neo4j_at": "",
                    }
                },
            )
            reset_count += 1

    return {
        "status": "success",
        "message": "Mongo sync status reset for threads missing in Neo4j",
        "reset_count": reset_count,
    }


def sync_all_threads_to_graph():
    synced_threads = 0
    skipped_threads = 0
    processed_comments = 0
    unique_comment_ids = set()

    # Erst Mongo Status korrigieren, falls Neo4j manuell gelöscht wurde
    reset_result = reset_mongo_sync_status_if_missing_in_neo4j()

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

        # Sicherheitsprüfung: Falls Thread doch schon in Neo4j existiert
        if thread_exists_in_neo4j(thread):
            skipped_threads += 1
            continue

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
        "reset_before_sync": reset_result,
        "synced_threads": synced_threads,
        "skipped_threads": skipped_threads,
        "processed_comments": processed_comments,
        "unique_comments": len(unique_comment_ids),
    }