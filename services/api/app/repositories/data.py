from collections import defaultdict
from app.db.mongo import MongoDB

mongo = MongoDB()

threads_collection = mongo.collection("threads")
comments_collection = mongo.collection("comments")


def get_all_threads():
    """
    Holt alle Threads inkl. source_file
    """
    threads = list(threads_collection.find({}, {"_id": 0}))

    # optional: absichern, falls source_file fehlt
    for t in threads:
        if "source_file" not in t:
            t["source_file"] = "unknown_source"

    return threads


def get_all_comments_grouped_by_thread():
    """
    Gruppiert Kommentare nach (source_file, thread_id)
    → wichtig für mehrere Datensätze!
    """
    grouped = defaultdict(list)

    for comment in comments_collection.find({}):
        # _id in string umwandeln (für Neo4j)
        comment["_id"] = str(comment["_id"])

        source_file = comment.get("source_file", "unknown_source")
        thread_id = comment.get("thread_id")

        if not thread_id:
            continue

        key = (source_file, thread_id)

        grouped[key].append(comment)

    return grouped