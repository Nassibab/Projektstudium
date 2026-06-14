class CounterSpeechSelector:
    def should_generate_counter_speech(
        self,
        comment: dict,
        shitstorm_score: float,
        warning_level: str
    ) -> bool:

        is_attack = int(comment.get("is_attacking", 0)) == 1
        attack_score = float(comment.get("attack_score", 1))
        toxicity_score = float(comment.get("toxicity_score", 1))
        attack_probability = float(comment.get("attack_probability", 0))

        thread_is_relevant = (
            shitstorm_score >= 50 or warning_level in ["warning", "critical"]
        )

        comment_is_relevant = (
            is_attack
            or attack_score >= 4
            or attack_probability >= 0.7
        )

        too_severe_for_counter_speech = toxicity_score >= 5

        return (
            thread_is_relevant
            and comment_is_relevant
            and not too_severe_for_counter_speech
        )