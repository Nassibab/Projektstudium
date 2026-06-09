from datetime import datetime, timedelta, timezone

WINDOW_MINUTES = 10

thread_store = {}


def parse_timestamp(value: str | None):
    if not value:
        return datetime.now(timezone.utc)

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def analyze_frequency(payload: dict):
    

    return {
        "Test"
    }