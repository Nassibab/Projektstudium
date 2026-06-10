from app.warning_services.window_store import WindowStore
from app.warning_services.window_aggregator import WindowAggregator
from app.warning_services.shitstorm_scorer import ShitstormScorer


class ModerationWarningService:
    def __init__(self, window_minutes=5, history_window_size=3):
        # speichert Kommentare
        self.store = WindowStore(window_minutes)
        # berechnet Fensterwerte
        self.aggregator = WindowAggregator(self.store)
        # berechnet Shitstorm-Score
        self.scorer = ShitstormScorer(history_window_size)

    #Funktion wird jedes Mal aufgerufen, wenn ein neuer Kommentar reinkomm
    def process_comment(self, comment):
        #Kommentar wird gespeichert.
        thread_id, window_start = self.store.add_comment(comment)
        #Aktuelles Fenster wird neu berechnet.
        metrics = self.aggregator.aggregate(thread_id, window_start)
        #Score wird berechnet.
        score = self.scorer.calculate_final_score(thread_id, metrics)

        return {
            "status": "success",
            "current_window_metrics": metrics,
            "shitstorm_prediction": score,
        }