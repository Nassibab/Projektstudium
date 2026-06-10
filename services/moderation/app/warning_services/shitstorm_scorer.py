from collections import defaultdict

#berechnet aus den aggregierten Fensterwerten einen Score.
class ShitstormScorer:
    def __init__(self, history_window_size=3):
        #Klasse merkt sich zusätzlich die Historie pro Thread.
        self.thread_history = defaultdict(list)
        self.history_window_size = history_window_size
   
    #Diese Funktion berechnet zuerst einen Score nur für das aktuelle Fenster
    def normalize(self, value, max_value):
        return min(value / max_value, 1.0)
    
    def calculate_window_score(self, metrics):
        score = (
            self.normalize(metrics["comment_count"], 50) * 0.3 +
            metrics["attack_ratio"] * 0.3 +
            metrics["toxic_ratio"] * 0.2 +
            self.normalize(metrics["unique_users"], 30) * 0.2
        )
        return round(score * 100, 2)
    

    #Diese Funktion berechnet den finalen Shitstorm-Score über mehrere Fenster
    def calculate_final_score(self, thread_id, metrics):
        #zuerst wird der aktuelle Window Score berechnet
        window_score = self.calculate_window_score(metrics)
        metrics["window_score"] = window_score

        #Dann wird dieses Fenster zur Historie gespeichert:
        self.thread_history[thread_id].append(metrics)
        recent_windows = self.thread_history[thread_id][-self.history_window_size:]

        #Dann werden die letzten 3 Fenster betrachtet: Der finale Score ist dann der Durchschnitt dieser Fenster.
        final_score = sum(w["window_score"] for w in recent_windows) / len(recent_windows)

        return {
            "thread_id": thread_id,
            "window_score": window_score,
            "final_shitstorm_score": round(final_score, 2),
            "recent_window_scores": [w["window_score"] for w in recent_windows],
            "warning_level": self.get_warning_level(final_score),
        }

    def get_warning_level(self, score):
        if score >= 75:
            return "critical"
        if score >= 50:
            return "warning"
        if score >= 30:
            return "watch"
        return "normal"