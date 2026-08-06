def map_thread(
    *,
    thread_id,
    title=None,
    comments_count=0,
    source_platform=None,
    source_type=None,
    extra=None,
):
    data = {
        "thread_id": thread_id,

        "title": title,
        "comments_count": comments_count,

        "source_platform": source_platform,
        "source_type": source_type,
       

    }

    if extra:
        data.update(extra)

    return data