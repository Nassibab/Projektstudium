from app.repositories.data import (
    get_all_threads,
    get_all_comments_grouped_by_thread,
)
from app.repositories.graph import save_thread_with_comments


def sync_all_threads_to_graph():
    synced_threads = 0
    synced_comments = 0

    threads = get_all_threads()
    comments_by_thread = get_all_comments_grouped_by_thread()

    for thread in threads:
        thread_id = thread["thread_id"]
        comments = comments_by_thread.get(thread_id, [])

        save_thread_with_comments(thread, comments)

        synced_threads += 1
        synced_comments += len(comments)

    return {
        "status": "success",
        "synced_threads": synced_threads,
        "synced_comments": synced_comments,
    }