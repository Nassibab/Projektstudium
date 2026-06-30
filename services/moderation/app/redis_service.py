import redis
import json
import os

redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"))

def push_to_dashboard(your_json_dict):
    redis_client.publish("thread_updates", json.dumps(your_json_dict))