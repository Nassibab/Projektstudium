import os

from slowapi import Limiter
from slowapi.util import get_remote_address

# Per-IP limit for LLM routes. slowapi format: "<count>/<period>" (second, minute, hour, day).
DEFAULT_RATE_LIMIT = "10/minute"


def get_rate_limit() -> str:
    return os.getenv("LLM_RATE_LIMIT", DEFAULT_RATE_LIMIT)


limiter = Limiter(key_func=get_remote_address)
