import json
import os

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CHANNEL_NAME = "thread-updates"


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
