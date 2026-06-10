from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter


class ThreadWindowAggregator:
    def __init__(self, window_minutes: int = 5):
        self.window_minutes = window_minutes

        # (thread_id, window_start) -> list of comments
        self.windows = defaultdict(list)

        # already closed windows
        self.closed_windows = set()

    def parse_time(self, value: str) -> datetime:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)

    def get_window_start(self, created_at: datetime) -> datetime:
        minute = (created_at.minute // self.window_minutes) * self.window_minutes
        return created_at.replace(minute=minute, second=0, microsecond=0)

    def get_window_end(self, window_start: datetime) -> datetime:
        return window_start + timedelta(minutes=self.window_minutes)

    def add_comment(self, comment: dict) -> dict:
        created_at = self.parse_time(comment["created_at"])
        thread_id = comment["thread_id"]

        window_start = self.get_window_start(created_at)
        key = (thread_id, window_start)

        self.windows[key].append(comment)

        return self.aggregate_window(thread_id, window_start)

    def aggregate_window(self, thread_id: str, window_start: datetime) -> dict:
        key = (thread_id, window_start)
        comments = self.windows[key]

        comment_count = len(comments)
        attack_count = sum(int(c.get("is_attacking", 0)) == 1 for c in comments)
        toxic_count = sum(float(c.get("toxicity_score", 1)) >= 4 for c in comments)
        reply_count = sum(c.get("parent") not in [None, 0, "0"] for c in comments)

        users = [c.get("login") for c in comments if c.get("login")]
        user_counts = Counter(users)

        unique_users = len(user_counts)
        dominant_user = user_counts.most_common(1)[0][0] if user_counts else None
        max_user_comments = user_counts.most_common(1)[0][1] if user_counts else 0

        return {
            "thread_id": thread_id,
            "window_start": window_start.isoformat(),
            "window_end": self.get_window_end(window_start).isoformat(),
            "window_size_minutes": self.window_minutes,

            "comment_count": comment_count,
            "reply_count": reply_count,
            "attack_count": attack_count,
            "toxic_count": toxic_count,

            "attack_ratio": round(attack_count / comment_count, 3) if comment_count else 0,
            "toxic_ratio": round(toxic_count / comment_count, 3) if comment_count else 0,
            "reply_ratio": round(reply_count / comment_count, 3) if comment_count else 0,

            "unique_users": unique_users,
            "dominant_user": dominant_user,
            "max_user_comments": max_user_comments,
            "dominant_user_ratio": round(max_user_comments / comment_count, 3) if comment_count else 0,
        }

    def close_old_windows(self, now: datetime | None = None) -> list[dict]:
        """
        Schließt alle Fenster, deren window_end <= now ist.
        Diese Funktion kannst du z.B. nach jedem neuen Kommentar oder per Scheduler aufrufen.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        closed_results = []

        for key in list(self.windows.keys()):
            thread_id, window_start = key
            window_end = self.get_window_end(window_start)

            if window_end <= now and key not in self.closed_windows:
                result = self.aggregate_window(thread_id, window_start)
                result["status"] = "closed"

                closed_results.append(result)
                self.closed_windows.add(key)

        return closed_results
    

aggregator = ThreadWindowAggregator(window_minutes=5)

comment_1 = {
    "id": 1,
    "thread_id": "thread_A",
    "created_at": "2026-01-01T12:01:00+00:00",
    "login": "user1",
    "parent": 0,
    "is_attacking": 1,
    "toxicity_score": 4
}

comment_2 = {
    "id": 2,
    "thread_id": "thread_A",
    "created_at": "2026-01-01T12:03:00+00:00",
    "login": "user2",
    "parent": 1,
    "is_attacking": 0,
    "toxicity_score": 2
}

print(aggregator.add_comment(comment_1))
print(aggregator.add_comment(comment_2))

closed = aggregator.close_old_windows(
    datetime.fromisoformat("2026-01-01T12:06:00+00:00")
)

print(closed)