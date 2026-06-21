import json
from datetime import datetime
from typing import Any, Optional, Tuple, Union

from app.db.mongo import MongoDB
from app.services.redis_events import get_redis_client
from pymongo.errors import PyMongoError

CACHE_KEY = "demo_data:threads"
MAX_THREADS = 50
KEEP_SCORE_THRESHOLD = 0.25

mongo = None
threads_collection = None
comments_collection = None


def _get_mongo_collections() -> Tuple[Optional[object], Optional[object]]:
    global mongo, threads_collection, comments_collection
    if mongo is None:
        try:
            mongo = MongoDB()
            threads_collection = mongo.collection("threads")
            comments_collection = mongo.collection("comments")
        except PyMongoError as exc:
            print(f"Warning: MongoDB unavailable in demo cache: {exc}")
            return None, None
        except Exception as exc:
            print(f"Warning: Failed to initialize MongoDB in demo cache: {exc}")
            return None, None
    return threads_collection, comments_collection


def _to_json(value: Any) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)


def _from_json(value: Union[str, bytes, None]) -> Any:
    if not value:
        return None
        
    if isinstance(value, bytes):
        value = value.decode("utf-8")
        
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to decode cached item from Redis: {e}")
        return None


def _parse_iso_datetime(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        return datetime.min

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.min


def _get_comment_score(comment: dict) -> float:
    try:
        return float(comment.get("score", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _get_thread_latest_score(item: dict) -> float:
    comments = item.get("thread", {}).get("comments") or []
    if not comments:
        return 0.0
    return _get_comment_score(comments[-1])


def _get_thread_latest_time(item: dict) -> datetime:
    comments = item.get("thread", {}).get("comments") or []
    if not comments:
        return datetime.min
    return _parse_iso_datetime(comments[-1].get("time") or comments[-1].get("created_at") or "")


def _trim_demo_items(items: list[dict]) -> list[dict]:
    items.sort(
        key=lambda x: (
            _get_thread_latest_score(x) > KEEP_SCORE_THRESHOLD, 
            _get_thread_latest_time(x)
        ), 
        reverse=True
    )
    return items[:MAX_THREADS]


def _build_demo_thread_item(thread: dict, comments: list[dict]) -> dict:
    sorted_comments = sorted(
        comments,
        key=lambda c: _parse_iso_datetime(c.get("created_at") or c.get("time") or ""),
    )
    demo_comments = []

    for comment in sorted_comments:
        demo_comments.append({
            "id": comment.get("comment_numeric_id") or comment.get("comment_id"),
            "author": comment.get("user") or comment.get("author"),
            "time": comment.get("created_at") or comment.get("time"),
            "text": comment.get("text", ""),
            "moderation": comment.get("moderation", ""),
            "kpis": comment.get("kpis") if isinstance(comment.get("kpis"), list) else [],
            "score": _get_comment_score(comment),
        })

    return {
        "thread": {
            "id": thread.get("thread_id"),
            "title": thread.get("title", ""),
            "text": thread.get("description") or thread.get("text") or thread.get("title") or "",
            "comments": demo_comments,
        }
    }


def load_demo_data_from_db() -> list[dict]:
    threads_col, comments_col = _get_mongo_collections()
    if not threads_col or not comments_col:
        return []

    try:
        threads = list(threads_col.find({}, {"_id": 0}))
        comments = list(comments_col.find({}, {"_id": 0}))
    except PyMongoError as exc:
        print(f"Warning: Could not load demo data from MongoDB: {exc}")
        return []

    if not threads:
        return []

    comments_by_thread: dict[Any, list[dict]] = {}
    for comment in comments:
        thread_id = comment.get("thread_id")
        if thread_id is None:
            continue
        comments_by_thread.setdefault(thread_id, []).append(comment)

    items = [
        _build_demo_thread_item(thread, comments_by_thread.get(thread.get("thread_id"), []))
        for thread in threads
    ]

    items = _trim_demo_items(items)
    return items


def get_cached_demo_data() -> list[dict]:
    client = get_redis_client()
    raw_items = client.lrange(CACHE_KEY, 0, -1)
    
    parsed_items = []
    for raw_item in raw_items:
        parsed = _from_json(raw_item)
        if parsed is not None:
            parsed_items.append(parsed)
            
    return parsed_items


def cache_demo_data(items: list[dict]) -> None:
    client = get_redis_client()
    with client.pipeline() as pipe:
        pipe.delete(CACHE_KEY)
        if items:
            pipe.rpush(CACHE_KEY, *[_to_json(item) for item in items])
        pipe.execute()


def ensure_cached_demo_data(force_refresh: bool = False) -> list[dict]:
    client = get_redis_client()
    
    if not force_refresh and client.exists(CACHE_KEY):
        return get_cached_demo_data()

    demo_items = load_demo_data_from_db()
    cache_demo_data(demo_items)
    return demo_items


def update_cached_demo_data(payload: dict) -> list[dict]:
    thread_id = payload.get("threadId")
    if thread_id is None:
        return get_cached_demo_data()

    items = get_cached_demo_data()
    thread_item = None
    
    for index, item in enumerate(items):
        if item.get("thread", {}).get("id") == thread_id:
            thread_item = items.pop(index)
            break

    if thread_item is None:
        threads_col, comments_col = _get_mongo_collections()
        if threads_col and comments_col:
            try:
                db_thread = threads_col.find_one({"thread_id": thread_id}, {"_id": 0})
                if db_thread:
                    db_comments = list(comments_col.find({"thread_id": thread_id}, {"_id": 0}))
                    thread_item = _build_demo_thread_item(db_thread, db_comments)
            except PyMongoError as exc:
                print(f"Warning: Could not query MongoDB while updating cached demo data: {exc}")

        if thread_item is None:
            thread_item = {
                "thread": {
                    "id": thread_id,
                    "title": payload.get("threadTitle", "New Thread"),
                    "text": payload.get("threadText", ""),
                    "comments": [],
                }
            }

    thread_comments = thread_item["thread"].setdefault("comments", [])
    thread_comments.append(payload.get("comment", {}))
    thread_item["thread"]["comments"] = thread_comments
    
    items.insert(0, thread_item)
    items = _trim_demo_items(items)
    cache_demo_data(items)
    
    return items