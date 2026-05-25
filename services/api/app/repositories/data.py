from collections import defaultdict
from app.db.mongo import MongoDB

mongo = MongoDB()

threads_collection = mongo.collection("threads")
comments_collection = mongo.collection("comments")


def get_all_threads():
    threads = list(threads_collection.find(
    {
        "$or": [
            {"synced_to_neo4j": {"$exists": False}},
            {"synced_to_neo4j": False}
        ]
    },
    {"_id": 0}
))

    for thread in threads:
        thread["source_file"] = thread.get("source_file") or thread.get("source_platform", "unknown_source")

    return threads


def get_all_comments_grouped_by_thread():
    grouped = defaultdict(list)

    for comment in comments_collection.find({}):
        comment["_id"] = str(comment["_id"])

        source_file = comment.get("source_file") or comment.get("source_platform", "unknown_source")
        thread_id = comment.get("thread_id")

        if not thread_id:
            continue

        key = (source_file, thread_id)
        grouped[key].append(comment)

    return grouped