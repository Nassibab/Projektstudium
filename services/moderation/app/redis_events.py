import json
import os

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CHANNEL_NAME = "frontend-updates"


def get_redis_client() -> redis.Redis:
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)


def publish_thread_update(payload: dict) -> int:
    client = get_redis_client()
    return client.publish(CHANNEL_NAME, json.dumps(payload))
