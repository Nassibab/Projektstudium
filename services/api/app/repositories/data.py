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

def save_analysis_results(payload: dict):
    db = MongoDB()

    comment_results = payload.get("comment_results", [])
    thread_results = payload.get("thread_results", [])
    user_results = payload.get("user_results", [])
    model_results = payload.get("model_results", [])

    bluesky_prediction_comments_results = payload.get(
        "bluesky_prediction_comments_results", []
    )
    bluesky_prediction_thread_results = payload.get(
        "bluesky_prediction_thread_results", []
    )
    bluesky_prediction_user_results = payload.get(
        "bluesky_prediction_user_results", []
    )
    bluesky_model_results = payload.get(
        "bluesky_model_results", []
    )

    if comment_results:
        db.collection("comment_analysis_results").delete_many({})
        db.collection("comment_analysis_results").insert_many(comment_results)

    if thread_results:
        db.collection("thread_analysis_results").delete_many({})
        db.collection("thread_analysis_results").insert_many(thread_results)

    if user_results:
        db.collection("user_analysis_results").delete_many({})
        db.collection("user_analysis_results").insert_many(user_results)

    if model_results:
        db.collection("model_results").insert_many(model_results)

    if bluesky_prediction_comments_results:
        db.collection("bluesky_prediction_comments_results").delete_many({})
        db.collection("bluesky_prediction_comments_results").insert_many(
            bluesky_prediction_comments_results
        )

    if bluesky_prediction_thread_results:
        db.collection("bluesky_prediction_thread_results").delete_many({})
        db.collection("bluesky_prediction_thread_results").insert_many(
            bluesky_prediction_thread_results
        )

    if bluesky_prediction_user_results:
        db.collection("bluesky_prediction_user_results").delete_many({})
        db.collection("bluesky_prediction_user_results").insert_many(
            bluesky_prediction_user_results
        )

    if bluesky_model_results:
        db.collection("bluesky_prediction_model_results").delete_many({})
        db.collection("bluesky_prediction_model_results").insert_many(
            bluesky_model_results
        )

    db.close()

    return {
        "status": "success",
        "comment_results": len(comment_results),
        "thread_results": len(thread_results),
        "user_results": len(user_results),
        "model_results": len(model_results),
        "bluesky_prediction_comments_results": len(bluesky_prediction_comments_results),
        "bluesky_prediction_thread_results": len(bluesky_prediction_thread_results),
        "bluesky_prediction_user_results": len(bluesky_prediction_user_results),
        "bluesky_model_results": len(bluesky_model_results),
    }