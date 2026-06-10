from collections import Counter

#berechnet aus mehreren Kommentaren EINES Fensters zusammenfassende Werte.
class WindowAggregator:
    #fragt den WindowStore ab und berechnet Metriken
    def __init__(self, window_store):
        self.window_store = window_store

    #Funktion nimmt ein bestimmtes Zeitfenster + Thread und berechnet daraus Kennzahlen
    def aggregate(self, thread_id, window_start):
        #alle Kommentare herausholen
        comments = self.window_store.get_comments(thread_id, window_start)
        #Anzahl aller Kommentare im Fenster.
        comment_count = len(comments)

        #zählt alle Kommentare, bei denen is_attacking = 1 ist 
        attack_count = sum(int(c.get("is_attacking", 0)) == 1 for c in comments)
        #Toxische Kommentare zählen
        toxic_count = sum(float(c.get("toxicity_score", 1)) >= 4 for c in comments)

        #Damit wird gezählt, wie viele verschiedene Nutzer beteiligt sind.
        users = [c.get("login") for c in comments if c.get("login")]
        user_counts = Counter(users)

        unique_users = len(user_counts)

        return {
            "thread_id": thread_id,
            "window_start": window_start.isoformat(),
            "window_end": self.window_store.get_window_end(window_start).isoformat(),
            "comment_count": comment_count,
            "attack_count": attack_count,
            "toxic_count": toxic_count,
            "attack_ratio": attack_count / comment_count if comment_count else 0,
            "toxic_ratio": toxic_count / comment_count if comment_count else 0,
            "unique_users": unique_users,
        }