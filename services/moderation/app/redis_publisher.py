import json
import os
import redis


REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_CHANNEL = os.getenv("REDIS_CHANNEL", "thread_updates")

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
)


def push_to_dashboard(data: dict) -> dict:
    """
    Sendet ein JSON-Event an das Dashboard über Redis Pub/Sub.
    Redis-Fehler sollen die Moderation nicht kaputt machen.
    """
    try:
        message = json.dumps(data, ensure_ascii=False, default=str)
        subscribers = redis_client.publish(REDIS_CHANNEL, message)

        return {
            "status": "published",
            "channel": REDIS_CHANNEL,
            "subscribers": subscribers,
        }

    except Exception as exc:
        return {
            "status": "failed",
            "channel": REDIS_CHANNEL,
            "error": str(exc),
        }