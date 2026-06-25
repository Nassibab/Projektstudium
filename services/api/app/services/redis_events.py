import json
import os

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CHANNEL_NAME = "frontend-updates"
CACHE_KEY = "latest_2_threads"


def get_redis_client() -> redis.Redis:
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)


def publish_thread_update(payload: dict) -> int:
    client = get_redis_client()
    return client.publish(CHANNEL_NAME, json.dumps(payload))


def iter_thread_updates():
    client = get_redis_client()
    pubsub = client.pubsub()
    pubsub.subscribe(CHANNEL_NAME)

    try:
        for message in pubsub.listen():
            if message.get("type") == "message":
                yield f"data: {message['data']}\n\n"
    finally:
        pubsub.close()

def set_cached_threads(threads_data: list):
    client = get_redis_client()
    client.set(CACHE_KEY, json.dumps(threads_data))

def get_cached_threads():
    client = get_redis_client()
    data = client.get(CACHE_KEY)
    if data:
        return json.loads(data)
    return None
