from app.db.mongo import get_db

db = get_db()

threads_collection = db["threads"]
comments_collection = db["comments"]


def get_all_threads():
    return list(threads_collection.find())


def get_thread_by_id(thread_id: str):
    return threads_collection.find_one({"thread_id": thread_id})


def get_comments_by_thread(thread_id: str):
    return list(comments_collection.find({"thread_id": thread_id}))


def insert_thread(thread: dict):
    return threads_collection.insert_one(thread)


def insert_comment(comment: dict):
    return comments_collection.insert_one(comment)


def get_all_comments():
    return list(comments_collection.find())