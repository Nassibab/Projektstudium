from collections import defaultdict
from app.db.mongo import MongoDB

import hashlib

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


def get_comments_for_analysis():
    comments = list(comments_collection.find({}, {"_id": 0}))
    threads = list(threads_collection.find({}, {"_id": 0}))

    threads_by_id = {
        t["thread_id"]: t
        for t in threads
    }

    result = []

    for c in comments:
        thread = threads_by_id.get(c.get("thread_id"), {})

        result.append({
            "id": c.get("comment_numeric_id"),
            "comment_id": c.get("comment_id"),
            "thread_id": c.get("thread_id"),
            "parent": c.get("parent_id"),
            "login": c.get("user"),
            "text": c.get("text"),
            "created": c.get("created_at"),

            "source_platform": c.get("source_platform"),
            "source_type": c.get("source_type"),

            "synthetic": c.get("synthetic"),
            "synthetic_role": c.get("synthetic_role"),
            "toxicity_level": c.get("toxicity_level"),
            "target_login": c.get("target_user"),

            "thread_title": thread.get("title"),
            "comments_count": thread.get("comments_count"),
            "scenario_type": thread.get("scenario_type"),
            "label_shitstorm": thread.get("label_shitstorm"),
        })

    return result