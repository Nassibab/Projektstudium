from collections import defaultdict
from app.db.mongo import MongoDB

mongo = MongoDB()

threads_collection = mongo.collection("threads")
comments_collection = mongo.collection("comments")


def get_all_threads():
    return list(threads_collection.find({}, {"_id": 0}))


def get_all_comments_grouped_by_thread():
    grouped = defaultdict(list)

    for comment in comments_collection.find({}, {"_id": 0}):
        grouped[comment["thread_id"]].append(comment)

    return grouped