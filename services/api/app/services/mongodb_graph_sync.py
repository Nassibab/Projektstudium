from app.repositories.data import (
    get_all_threads,
    get_thread_by_id,
    get_comments_by_thread,
)
from app.repositories.graph import save_thread_with_comments


def sync_all_threads_to_graph():
    synced_threads = 0
    synced_comments = 0

    threads = get_all_threads()

    for thread in threads:
        thread_id = thread["thread_id"]
        comments = get_comments_by_thread(thread_id)

        save_thread_with_comments(thread, comments)

        synced_threads += 1
        synced_comments += len(comments)

    return {
        "status": "success",
        "synced_threads": synced_threads,
        "synced_comments": synced_comments,
    }


def sync_single_thread_to_graph(thread_id: str):
    thread = get_thread_by_id(thread_id)

    if not thread:
        return {
            "status": "not_found",
            "message": f"Thread {thread_id} wurde nicht gefunden",
        }

    comments = get_comments_by_thread(thread_id)

    save_thread_with_comments(thread, comments)

    return {
        "status": "success",
        "thread_id": thread_id,
        "synced_comments": len(comments),
    }