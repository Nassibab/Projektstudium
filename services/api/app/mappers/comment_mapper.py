import hashlib

def make_numeric_id(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest(), 16) % 10**12


def map_comment(
    *,
    comment_id,
    thread_id,
    user,
    text,
    parent_id=None,
    created_at=None,
    source_platform=None,
    source_type=None,
    extra=None,
):
    data = {
        "comment_id": comment_id,
        "comment_numeric_id": make_numeric_id(str(comment_id)),
        
        "thread_id": thread_id,
        "parent_id": parent_id,

        "user": user,

        "text": text,
        "created_at": created_at,

        "source_platform": source_platform,

        "source_type": source_type,
    }

    if extra:
        data.update(extra)

    return data