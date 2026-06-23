class WindowAggregator:
    """
    Berechnet reine Fenster-Messwerte aus den festen Analyse-R-Metriken.
    """

    REQUIRED_ANALYSE_R_FIELDS = [
        "is_long_thread",
        "created_at",
        "id",
        "synthetic_role",
        "irony",
        "negative_word_count",
        "insult_count",
        "is_attacking",
        "attack_score",
        "swearword_count",
        "toxicity_score",
        "direct_address_count",
        "imperative_count",
        "accusation_marker_count",
        "mockery_marker_count",
        "login_count",
        "login_percentage",
        "frequency_group",
        "date_timestamp",
        "thread_position_abs",
        "thread_size",
        "thread_position_rel",
        "num_previous_comments",
        "is_thread_start",
        "is_reply",
        "previous_comment_exists",
        "time_since_thread_start",
        "time_since_previous_comment",
        "user_thread_comment_count_before",
        "user_thread_comment_count_total",
        "user_previous_thread_share",
        "reply_depth",
        "num_children",
        "parent_is_root",
        "is_target_login_numeric",
        "thread_user_count",
        "thread_comment_count",
        "thread_mean_comments_per_user",
        "thread_max_comments_by_one_user",
        "thread_single_comment_user_count",
        "thread_max_user_share",
        "thread_single_comment_user_share",
        "log_time_since_thread_start",
        "log_time_since_previous_comment",
        "previous_comment_attack",
        "prev_attack_count",
        "prev_attack_rate",
        "prev_toxicity_score_mean",
        "prev_toxicity_score_max",
        "prev_attack_score_max",
        "recent_attack_rate_3",
        "recent_attack_rate_5",
        "attack_streak_current",
        "target_recently_attacked",
        "reply_after_attack",
        "target_response_context_score",
    ]

    def __init__(self, window_store):
        self.window_store = window_store

    def _validate_comment(self, comment):
        missing = [field for field in self.REQUIRED_ANALYSE_R_FIELDS if field not in comment]
        if missing:
            raise KeyError(f"Kommentar enthält nicht alle festen Analyse-R-Metriken. Fehlend: {missing}")

    def _to_float(self, value, field_name):
        try:
            return float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Feld '{field_name}' muss numerisch interpretierbar sein. Wert: {value!r}")

    def _to_int(self, value, field_name):
        try:
            return int(float(value))
        except (ValueError, TypeError):
            raise ValueError(f"Feld '{field_name}' muss als Integer interpretierbar sein. Wert: {value!r}")

    def _mean(self, values):
        return sum(values) / len(values) if values else 0.0

    def aggregate(self, thread_id, window_start):
        comments = self.window_store.get_comments(thread_id, window_start)

        for comment in comments:
            self._validate_comment(comment)

        comment_count = len(comments)
        if comment_count == 0:
            raise ValueError("Für das angeforderte Fenster liegen keine Kommentare vor.")

        attack_scores = [
            self._to_float(c["attack_score"], "attack_score")
            for c in comments
        ]
        toxicity_scores = [
            self._to_float(c["toxicity_score"], "toxicity_score")
            for c in comments
        ]
        insult_counts = [
            self._to_float(c["insult_count"], "insult_count")
            for c in comments
        ]
        swearword_counts = [
            self._to_float(c["swearword_count"], "swearword_count")
            for c in comments
        ]
        negative_word_counts = [
            self._to_float(c["negative_word_count"], "negative_word_count")
            for c in comments
        ]
        direct_address_counts = [
            self._to_float(c["direct_address_count"], "direct_address_count")
            for c in comments
        ]
        accusation_marker_counts = [
            self._to_float(c["accusation_marker_count"], "accusation_marker_count")
            for c in comments
        ]
        mockery_marker_counts = [
            self._to_float(c["mockery_marker_count"], "mockery_marker_count")
            for c in comments
        ]
        irony_values = [
            self._to_float(c["irony"], "irony")
            for c in comments
        ]
        recent_attack_rate_3_values = [
            self._to_float(c["recent_attack_rate_3"], "recent_attack_rate_3")
            for c in comments
        ]
        recent_attack_rate_5_values = [
            self._to_float(c["recent_attack_rate_5"], "recent_attack_rate_5")
            for c in comments
        ]
        attack_streak_values = [
            self._to_float(c["attack_streak_current"], "attack_streak_current")
            for c in comments
        ]
        target_recently_attacked_values = [
            self._to_int(c["target_recently_attacked"], "target_recently_attacked")
            for c in comments
        ]
        reply_after_attack_values = [
            self._to_int(c["reply_after_attack"], "reply_after_attack")
            for c in comments
        ]
        reply_depth_values = [
            self._to_float(c["reply_depth"], "reply_depth")
            for c in comments
        ]
        num_children_values = [
            self._to_float(c["num_children"], "num_children")
            for c in comments
        ]

        # Feste Angriffsdefinition 
        # Im Projektkontext gilt attack_score >= 5 als Angriff.
        attack_count = sum(1 for value in attack_scores if value >= 5)
        toxic_count = sum(1 for value in toxicity_scores if value >= 4)
        insult_comment_count = sum(1 for value in insult_counts if value > 0)
        swearword_comment_count = sum(1 for value in swearword_counts if value > 0)

        thread_user_count = max(
            self._to_int(c["thread_user_count"], "thread_user_count")
            for c in comments
        )
        thread_comment_count = max(
            self._to_int(c["thread_comment_count"], "thread_comment_count")
            for c in comments
        )
        thread_max_user_share = max(
            self._to_float(c["thread_max_user_share"], "thread_max_user_share")
            for c in comments
        )

        return {
            "thread_id": thread_id,
            "window_start": window_start.isoformat(),
            "window_end": self.window_store.get_window_end(window_start).isoformat(),

            # Aktivität / Frequenz
            "comment_count": comment_count,
            "thread_user_count": thread_user_count,
            "thread_comment_count": thread_comment_count,
            "thread_max_user_share": round(thread_max_user_share, 3),

            # Angriff / Aggression
            "attack_count": attack_count,
            "attack_ratio": round(attack_count / comment_count, 3),
            "attack_score_mean": round(self._mean(attack_scores), 3),
            "attack_score_max": max(attack_scores),

            # Toxizität
            "toxic_count": toxic_count,
            "toxic_ratio": round(toxic_count / comment_count, 3),
            "toxicity_score_mean": round(self._mean(toxicity_scores), 3),
            "toxicity_score_max": max(toxicity_scores),

            # Negative Sprache
            "insult_comment_count": insult_comment_count,
            "insult_ratio": round(insult_comment_count / comment_count, 3),
            "insult_count_sum": round(sum(insult_counts), 3),
            "swearword_comment_count": swearword_comment_count,
            "swearword_ratio": round(swearword_comment_count / comment_count, 3),
            "negative_word_count_mean": round(self._mean(negative_word_counts), 3),

            # Zielgerichteter Konflikt / Personalisierung
            "direct_address_mean": round(self._mean(direct_address_counts), 3),
            "accusation_marker_mean": round(self._mean(accusation_marker_counts), 3),
            "mockery_marker_mean": round(self._mean(mockery_marker_counts), 3),
            "target_recently_attacked_ratio": round(
                sum(target_recently_attacked_values) / comment_count,
                3,
            ),

            # Eskalationsdynamik
            "recent_attack_rate_3_mean": round(self._mean(recent_attack_rate_3_values), 3),
            "recent_attack_rate_5_mean": round(self._mean(recent_attack_rate_5_values), 3),
            "attack_streak_max": max(attack_streak_values),
            "reply_after_attack_ratio": round(sum(reply_after_attack_values) / comment_count, 3),

            # Erklärung / Debug, nicht Hauptscore
            "irony_mean": round(self._mean(irony_values), 3),
            "reply_depth_mean": round(self._mean(reply_depth_values), 3),
            "reply_depth_max": max(reply_depth_values),
            "num_children_mean": round(self._mean(num_children_values), 3),
        }
