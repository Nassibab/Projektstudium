from app.repositories.data import (
    get_all_threads,
    get_all_comments_grouped_by_thread,
)
from app.repositories.graph import save_thread_with_comments


def sync_all_threads_to_graph():
    synced_threads = 0
    processed_comments = 0
    unique_comment_ids = set()

    threads = get_all_threads()
    comments_by_thread = get_all_comments_grouped_by_thread()

    for thread in threads:
        source_file = thread.get("source_file", "unknown_source")
        thread_id = thread["thread_id"]

        # Wichtig: Kommentare nach Dataset + Thread holen
        key = (source_file, thread_id)
        comments = comments_by_thread.get(key, [])

        save_thread_with_comments(thread, comments)

        synced_threads += 1
        processed_comments += len(comments)

        for comment in comments:
            comment_id = comment.get("_id")
            if comment_id:
                unique_comment_ids.add(str(comment_id))

    return {
        "status": "success",
        "synced_threads": synced_threads,
        "processed_comments": processed_comments,
        "unique_comments": len(unique_comment_ids),
    }