import logging
import time

import requests

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = [1, 2]
RETRYABLE_STATUS = {502, 503, 504}


def request_with_retry(method: str, url: str, **kwargs) -> requests.Response:
    """HTTP request that retries transient failures only.

    Retries connection errors, timeouts and HTTP 502/503/504 up to MAX_ATTEMPTS
    times with a 1s/2s backoff. 4xx responses are returned immediately and never
    retried, since they indicate a client-side problem that a retry won't fix.
    """

    last_exc: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.request(method, url, **kwargs)

            if response.status_code in RETRYABLE_STATUS and attempt < MAX_ATTEMPTS:
                logger.warning(
                    "[http_retry] %s %s -> %s (attempt %s/%s), retrying",
                    method, url, response.status_code, attempt, MAX_ATTEMPTS,
                )
                time.sleep(BACKOFF_SECONDS[attempt - 1])
                continue

            return response

        except (requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc

            if attempt < MAX_ATTEMPTS:
                logger.warning(
                    "[http_retry] %s %s failed (%s) (attempt %s/%s), retrying",
                    method, url, type(exc).__name__, attempt, MAX_ATTEMPTS,
                )
                time.sleep(BACKOFF_SECONDS[attempt - 1])
                continue

            raise

    # Defensive: loop always returns or raises, but keep type checkers happy.
    raise last_exc if last_exc else RuntimeError("request_with_retry exhausted")


def get(url: str, **kwargs) -> requests.Response:
    return request_with_retry("GET", url, **kwargs)


def post(url: str, **kwargs) -> requests.Response:
    return request_with_retry("POST", url, **kwargs)
