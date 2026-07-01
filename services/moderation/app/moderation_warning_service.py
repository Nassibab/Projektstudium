from app.warning_services.window_store import WindowStore
from app.warning_services.window_aggregator import WindowAggregator
from app.warning_services.shitstorm_scoring.scorer import ShitstormScorer

from app.measure_services.countermeasure_service import CountermeasureService
from app.measure_services.counter_speech_selector import CounterSpeechSelector
from app.measure_services.counter_speech_generator_extended import CounterSpeechGenerator

from app.redis_publisher import push_to_dashboard


class ModerationWarningService:
    def __init__(
        self,
        window_minutes: int = 5,
        history_window_size: int = 5,
        rolling_window_size: int | None = None,
        min_history: int = 3,
        z_watch: float = 1.0,
        z_full: float = 3.0,
        cusum_reference: float = 0.5,
        cusum_watch: float = 1.5,
        cusum_full: float = 5.0,
        watch_threshold: float = 0.20,
        warning_threshold: float = 0.40,
        critical_threshold: float = 0.60,
        core_watch_threshold: float = 0.20,
        core_warning_threshold: float = 0.40,
        support_threshold: float = 0.20,
    ):
        """
        window_minutes:
            Größe des festen Aggregationsfensters in Minuten, z. B. 5 oder 10.

        rolling_window_size:
            Anzahl früherer Fenster, die als Rolling-Historie für z-Score und
            CUSUM verwendet werden. Wenn None, wird history_window_size genutzt.

        history_window_size:
            Rückwärtskompatibler Name für rolling_window_size.
        """
        if window_minutes < 1:
            raise ValueError("window_minutes must be >= 1")

        if rolling_window_size is None:
            rolling_window_size = history_window_size
        if rolling_window_size < 1:
            raise ValueError("rolling_window_size must be >= 1")
        if min_history < 1:
            raise ValueError("min_history must be >= 1")
        if min_history > rolling_window_size:
            raise ValueError("min_history must be <= rolling_window_size")

        self.window_minutes = window_minutes
        self.rolling_window_size = rolling_window_size
        self.min_history = min_history

        self.store = WindowStore(window_minutes)
        self.aggregator = WindowAggregator(self.store)

        self.scorer = ShitstormScorer(
            history_window_size=rolling_window_size,
            min_history=min_history,
            dimension_combiner="mean",
            z_watch=z_watch,
            z_full=z_full,
            cusum_reference=cusum_reference,
            cusum_watch=cusum_watch,
            cusum_full=cusum_full,
            watch_threshold=watch_threshold,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
        )

        self.countermeasures = CountermeasureService()
        self.counter_speech_selector = CounterSpeechSelector()
        self.counter_speech_generator = CounterSpeechGenerator()

    def process_comment(self, comment):
        thread_id, window_start = self.store.add_comment(comment)
        metrics = self.aggregator.aggregate(thread_id, window_start)

        score_result = self.scorer.calculate_final_score(
            thread_id=thread_id,
            metrics=metrics,
        )

        countermeasure_result = self.countermeasures.decide_actions(
            score_result["shitstorm_barometer"],
            warning_level=score_result["warning_level"],
        )

        should_generate_counter_speech = (
            self.counter_speech_selector.should_generate_counter_speech(
                comment=comment,
                shitstorm_score=score_result["shitstorm_barometer"],
                warning_level=score_result["warning_level"],
            )
        )

        counter_speech_text = None
        counter_speech_error = None
        if should_generate_counter_speech:
            try:
                counter_speech_text = self.counter_speech_generator.generate_for_comment(
                    comment=comment,
                    previous_comments=comment.get("previous_comments"),
                    thread_context=comment.get("thread_context"),
                )
            except Exception as exc:  # Generator-Fehler sollen die Warnberechnung nicht abbrechen.
                counter_speech_error = str(exc)

        return {
            "status": "success",
            "comment_id": comment.get("comment_id"),
            "thread_id": thread_id,
            "current_window_metrics": metrics,
            "shitstorm_prediction": score_result,
            "countermeasures": countermeasure_result,
            "counter_speech": {
                "should_generate": should_generate_counter_speech,
                "reason": (
                    "Comment is suitable for counter speech."
                    if should_generate_counter_speech
                    else "Counter speech is not required for this comment."
                ),
                "generated_text": counter_speech_text,
                "error": counter_speech_error,
            },
        }

  def process_warning_payload(self, payload: dict):
    """Verarbeitet den Live-Payload aus /moderation/warning.

    Der Payload enthält `latest_comment` plus `previous_comments`. Für die
    Score-Berechnung wird der aktuelle Kommentar wie bisher verarbeitet;
    für die neue Gegenrede wird der Verlauf an den Generator weitergereicht.
    """
    latest_comment = dict(payload.get("latest_comment") or {})
    if not latest_comment:
        raise ValueError("Payload enthält keinen latest_comment.")

    previous_comments = payload.get("previous_comments") or []
    thread = payload.get("thread") or {}

    latest_comment.setdefault(
        "thread_id",
        thread.get("thread_id") or payload.get("thread_id"),
    )
    latest_comment.setdefault("source_platform", payload.get("platform"))
    latest_comment.setdefault("source_file", payload.get("source_file"))
    latest_comment["previous_comments"] = previous_comments

    if not latest_comment.get("thread_context"):
        latest_comment["thread_context"] = (
            payload.get("thread_context")
            or thread.get("text")
            or thread.get("title")
            or ""
        )

    result = self.process_comment(latest_comment)

    redis_event = {
        "event": "moderation_warning_updated",
        "thread_id": result.get("thread_id"),
        "comment_id": result.get("comment_id"),
        "warning_level": result.get("shitstorm_prediction", {}).get("warning_level"),
        "shitstorm_barometer": result.get("shitstorm_prediction", {}).get("shitstorm_barometer"),
        "evaluation_status": result.get("shitstorm_prediction", {}).get("evaluation_status"),
        "payload": result,
    }

    result["redis_publish"] = push_to_dashboard(redis_event)

    return result
