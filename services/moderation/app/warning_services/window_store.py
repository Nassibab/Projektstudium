from datetime import datetime, timedelta
from collections import defaultdict

#NUr Speichern und Zuordnen von Kommentaren zu Zeitfenstern 
class WindowStore:
    def __init__(self, window_minutes=5):
        # Fenstergröße
        self.window_minutes = window_minutes
        # Speicherung der Kommentare
        self.windows = defaultdict(list)

    # wandelt einen Zeitstring in ein Python-Datum um
    def parse_time(self, value):
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    
    # berechnet den Start des passenden Zeitfensters (bei 5min: 12:01 → 12:00, 12:06 → 12:05)
    # drch Rundung nach unten.
    def get_window_start(self, created_at):
        minute = (created_at.minute // self.window_minutes) * self.window_minutes
        return created_at.replace(minute=minute, second=0, microsecond=0)

    def get_window_end(self, window_start):
        return window_start + timedelta(minutes=self.window_minutes)
    
    ####### nimmt einen Kommentar entgegen ###########
    def add_comment(self, comment):
        created_at = self.parse_time(comment["created_at"])
        thread_id = comment["id"]
        window_start = self.get_window_start(created_at)

        # Kommentar speichern
        key = (thread_id, window_start)
        self.windows[key].append(comment)

        return key

    def get_comments(self, thread_id, window_start):
        return self.windows[(thread_id, window_start)]