from datetime import datetime, timedelta
from collections import defaultdict


class WindowStore:
    """
    Speichert Kommentare nach thread_id und festem Zeitfenster.

    - thread_id muss als technisches Feld im eingehenden Payload vorhanden sein.
    - created_at muss vorhanden sein.
    """

    def __init__(self, window_minutes=5):
        self.window_minutes = window_minutes
        self.windows = defaultdict(list)

    def parse_time(self, value):
        if isinstance(value, datetime):
            return value

        value = str(value).strip()
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")

        return datetime.fromisoformat(value)

    def get_window_start(self, created_at):
        minute = (created_at.minute // self.window_minutes) * self.window_minutes
        return created_at.replace(minute=minute, second=0, microsecond=0)

    def get_window_end(self, window_start):
        return window_start + timedelta(minutes=self.window_minutes)

    def add_comment(self, comment):
        created_at = self.parse_time(comment["created_at"])
        thread_id = comment["thread_id"]
        window_start = self.get_window_start(created_at)

        self.windows[(thread_id, window_start)].append(comment)

        return thread_id, window_start

    def get_comments(self, thread_id, window_start):
        return self.windows[(thread_id, window_start)]
