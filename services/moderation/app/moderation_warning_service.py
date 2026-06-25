from app.warning_services.window_store import WindowStore
from app.warning_services.window_aggregator import WindowAggregator
from app.warning_services.shitstorm_scoring.scorer import ShitstormScorer

from app.measure_services.countermeasure_service import CountermeasureService
from app.measure_services.counter_speech_selector import CounterSpeechSelector
from app.measure_services.counter_speech_generator import CounterSpeechGenerator
from app.redis_events import publish_thread_update


class ModerationWarningService:
    def __init__(self, window_minutes=5, history_window_size=3):
        # Scorer einmalig korrekt initialisieren
        self.scorer = ShitstormScorer(
            history_window_size=history_window_size,
            min_history=3,
            dimension_combiner="mean",
        )
        self.store = WindowStore(window_minutes)
        self.aggregator = WindowAggregator(self.store)

        self.countermeasures = CountermeasureService()
        self.counter_speech_selector = CounterSpeechSelector()
        self.counter_speech_generator = CounterSpeechGenerator()

    def process_comment(self, comment: dict, is_batch: bool = False):
        # 1. Metriken bestimmen (Live vs Batch)
        if is_batch:
            # Batch: Keine Zeitfenster, keine History, keine Aggregation
            metrics = {
                "comment_count": 1,
                "toxicity_score": float(comment.get("toxicity_score", 0.0)),
                "attack_score": float(comment.get("attack_score", 0.0)),
                "attack_streak_max": 0,
            }
            # Statische Berechnung (wir rufen direkt den Scorer auf)
            # Wir nehmen hier eine vereinfachte Version ohne History-Check
            score_result = {
                "shitstorm_barometer": round(metrics["toxicity_score"] * 10, 2),
                "warning_level": "Normal" if metrics["toxicity_score"] < 0.25 else "Warnung",
                "dimension_scores": {
                    "Toxizität": metrics["toxicity_score"],
                    "Angriff": metrics["attack_score"]
                }
            }
            countermeasure_result = {}
            should_generate_counter_speech = False
            counter_speech_text = None
            thread_id = comment.get("thread_id", "unknown")
        else:
            # Live-Pipeline (mit Zeitfenstern)
            thread_id, window_start = self.store.add_comment(comment)
            metrics = self.aggregator.aggregate(thread_id, window_start)
            score_result = self.scorer.calculate_final_score(thread_id=thread_id, metrics=metrics)
            
            countermeasure_result = self.countermeasures.decide_actions(
                score_result["shitstorm_barometer"], warning_level=score_result["warning_level"]
            )
            should_generate_counter_speech = self.counter_speech_selector.should_generate_counter_speech(
                comment=comment, shitstorm_score=score_result["shitstorm_barometer"], warning_level=score_result["warning_level"]
            )
            counter_speech_text = self.counter_speech_generator.generate(comment, comment.get("thread_context", "")) if should_generate_counter_speech else None

        # 2. Frontend-Struktur (für beide Modi gleich)
        moderation_level = score_result["warning_level"]
        score_value = round(score_result["shitstorm_barometer"] / 100, 4)

        frontend_comment = {
            "id": comment.get("id"),
            "author": comment.get("author") or comment.get("user") or "Unbekannt",
            "time": comment.get("created_at") or comment.get("time") or comment.get("timestamp"),
            "text": comment.get("text", ""),
            "moderation": moderation_level,
            "score": score_value,
            "kpis": [
                {"name": "Toxizität", "value": round(float(comment.get("toxicity_score", 0.0)) / 10, 4)},
                {"name": "Angriff", "value": round(float(comment.get("attack_score", 0.0)) / 10, 4)},
            ],
            "countermeasures": countermeasure_result,
            "counter_speech": {
                "should_generate": should_generate_counter_speech,
                "generated_text": counter_speech_text,
            },
        }

        # 3. Payload für Redis/API
        payload = {
            "type": "comment_added",
            "threadId": thread_id,
            "comment": frontend_comment,
            "moderation_result": score_result
        }

        # Nur im Live-Modus via Redis streamen
        if not is_batch:
            publish_thread_update(payload)

        return payload