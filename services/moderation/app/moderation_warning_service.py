from app.warning_services.window_store import WindowStore
from app.warning_services.window_aggregator import WindowAggregator
from app.warning_services.shitstorm_scoring.scorer import ShitstormScorer

from app.measure_services.countermeasure_service import CountermeasureService
from app.measure_services.counter_speech_selector import CounterSpeechSelector
from app.measure_services.counter_speech_generator import CounterSpeechGenerator


class ModerationWarningService:
    def __init__(self, window_minutes=5, history_window_size=5):
        self.store = WindowStore(window_minutes)
        self.aggregator = WindowAggregator(self.store)

        self.scorer = ShitstormScorer(
            history_window_size=history_window_size,
            min_history=3,
            dimension_combiner="mean",
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
        if should_generate_counter_speech:
            counter_speech_text = self.counter_speech_generator.generate(
                comment=comment,
                thread_context=comment.get("thread_context", ""),
            )

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
            },
        }
