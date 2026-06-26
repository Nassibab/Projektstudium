from __future__ import annotations

from collections import Counter
from typing import Any


class WindowAggregator:
    """
    Aggregiert Kommentare direkt zu Fenster-Metriken.

    """

    REQUIRED_STANDARD_FIELDS = [
        "comment_id",
        "thread_id",
        "login",
        "text",
        "created_at",
        "parent_id",
        "irony",
        "attack_score",
        "toxicity_score",
        "swearword_count",
        "negative_word_count",
        "insult_count",
        "direct_address_count",
        "imperative_count",
        "accusation_marker_count",
        "mockery_marker_count",
        "is_attacking",
        "reply_depth",
        "parent_is_root",
        "num_children",
        "thread_position_abs",
        "thread_position_rel",
        "num_previous_comments",
        "prev_attack_rate",
        "prev_toxicity_score_mean",
        "prev_attack_count",
        "prev_toxicity_score_max",
        "prev_attack_score_max",
        "recent_attack_rate_3",
        "recent_attack_rate_5",
        "attack_streak_current",
        "target_recently_attacked",
        "reply_after_attack",
        "target_response_context_score",
        "predicted_synthetic_role",
        "predicted_synthetic_role_label",
        "prob_class_1",
        "prob_class_2",
        "prob_class_3",
        "prob_class_4",
        "prob_class_5",
        "prob_class_6",
        "prob_class_7",
    ]

    def __init__(self, window_store):
        self.window_store = window_store

    def _validate_comment(self, comment: dict[str, Any]) -> None:
        missing = [field for field in self.REQUIRED_STANDARD_FIELDS if field not in comment]
        if missing:
            raise KeyError(
                "Kommentar entspricht nicht dem neuen Standardformat. "
                f"Fehlende Felder: {missing}"
            )

    @staticmethod
    def _to_float(value: Any, field_name: str, default: float | None = None) -> float:
        try:
            if value is None:
                if default is not None:
                    return default
                raise ValueError
            return float(value)
        except (ValueError, TypeError):
            if default is not None:
                return default
            raise ValueError(
                f"Feld '{field_name}' muss numerisch interpretierbar sein. Wert: {value!r}"
            )

    @staticmethod
    def _to_int(value: Any, field_name: str, default: int | None = None) -> int:
        try:
            if value is None:
                if default is not None:
                    return default
                raise ValueError
            return int(float(value))
        except (ValueError, TypeError):
            if default is not None:
                return default
            raise ValueError(
                f"Feld '{field_name}' muss als Integer interpretierbar sein. Wert: {value!r}"
            )

    @staticmethod
    def _mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def _clamp_0_1(value: float) -> float:
        return max(0.0, min(1.0, value))

    def _all_seen_thread_comments(self, thread_id: str) -> list[dict[str, Any]]:
        """Alle bisher im RAM gesehenen Kommentare dieses Threads."""
        rows: list[dict[str, Any]] = []

        for (stored_thread_id, _window_start), comments in self.window_store.windows.items():
            if stored_thread_id == thread_id:
                rows.extend(comments)

        return rows

    def _is_attack_comment(self, comment: dict[str, Any]) -> int:
        attack_score = self._to_float(comment.get("attack_score"), "attack_score", 0.0)
        is_attacking = self._to_int(comment.get("is_attacking"), "is_attacking", 0)
        role_label = str(comment.get("predicted_synthetic_role_label", "")).lower()
        role_id = str(comment.get("predicted_synthetic_role", ""))

        # Das binäre Feld aus dem Standardformat ist die primäre harte Labelsäule.
        # attack_score >= 5 bleibt zusätzliche Sicherheitsregel auf der 1-10-Skala.
        # Rollenklasse 5 / Label attack zählt ebenfalls als Angriffssignal.
        return int(
            is_attacking == 1
            or attack_score >= 5
            or role_label == "attack"
            or role_id == "5"
        )

    def aggregate(self, thread_id, window_start):
        comments = self.window_store.get_comments(thread_id, window_start)

        for comment in comments:
            self._validate_comment(comment)

        comment_count = len(comments)
        if comment_count == 0:
            raise ValueError("Für das angeforderte Fenster liegen keine Kommentare vor.")

        all_thread_comments = self._all_seen_thread_comments(thread_id)
        all_thread_comments_count = len(all_thread_comments)

        logins = [str(c.get("login", "")) for c in comments]
        login_counts = Counter(logins)
        unique_users = len(login_counts)
        dominant_user_ratio = (
            max(login_counts.values()) / comment_count
            if login_counts
            else 0.0
        )

        thread_logins = [str(c.get("login", "")) for c in all_thread_comments]
        thread_login_counts = Counter(thread_logins)
        thread_user_count = len(thread_login_counts)
        thread_max_comments_by_one_user = (
            max(thread_login_counts.values())
            if thread_login_counts
            else 0
        )
        thread_single_comment_user_count = sum(
            1 for count in thread_login_counts.values()
            if count == 1
        )
        thread_mean_comments_per_user = (
            all_thread_comments_count / thread_user_count
            if thread_user_count
            else 0.0
        )
        thread_max_user_share = (
            thread_max_comments_by_one_user / all_thread_comments_count
            if all_thread_comments_count
            else 0.0
        )
        thread_single_comment_user_share = (
            thread_single_comment_user_count / thread_user_count
            if thread_user_count
            else 0.0
        )

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
        imperative_counts = [
            self._to_float(c["imperative_count"], "imperative_count")
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
        attack_probability_values = [
            self._to_float(c.get("prob_class_5"), "prob_class_5", 0.0)
            for c in comments
        ]
        counter_speech_probability_values = [
            self._to_float(c.get("prob_class_4"), "prob_class_4", 0.0)
            for c in comments
        ]
        target_response_probability_values = [
            self._to_float(c.get("prob_class_6"), "prob_class_6", 0.0)
            for c in comments
        ]
        deescalation_probability_values = [
            self._to_float(c.get("prob_class_7"), "prob_class_7", 0.0)
            for c in comments
        ]

        attack_flags = [self._is_attack_comment(c) for c in comments]

        # toxicity_score-Skala: 1=nicht toxisch, 2=leicht toxisch,
        # 3=toxisch, 4=stark toxisch. toxic_count zählt echte Toxizität ab 3.
        toxic_flags = [int(value >= 3) for value in toxicity_scores]

        insult_comment_count = sum(1 for value in insult_counts if value > 0)
        swearword_comment_count = sum(1 for value in swearword_counts if value > 0)

        attack_score_mean = self._mean(attack_scores)
        toxicity_score_mean = self._mean(toxicity_scores)

        return {
            "thread_id": thread_id,
            "window_start": window_start.isoformat(),
            "window_end": self.window_store.get_window_end(window_start).isoformat(),

            # Aktivität / Frequenz im aktuellen Fenster
            "comment_count": comment_count,
            "unique_users": unique_users,
            "dominant_user_ratio": round(dominant_user_ratio, 3),
            "multi_user_ratio": round(1.0 - dominant_user_ratio, 3),

            # Bisher im laufenden Service gesehener Thread-Kontext
            "thread_user_count": thread_user_count,
            "thread_comment_count": all_thread_comments_count,
            "thread_mean_comments_per_user": round(thread_mean_comments_per_user, 3),
            "thread_max_comments_by_one_user": thread_max_comments_by_one_user,
            "thread_single_comment_user_count": thread_single_comment_user_count,
            "thread_max_user_share": round(thread_max_user_share, 3),
            "thread_single_comment_user_share": round(thread_single_comment_user_share, 3),

            # Angriff / Aggression
            "attack_count": sum(attack_flags),
            "attack_ratio": round(sum(attack_flags) / comment_count, 3),
            "attack_score_mean": round(attack_score_mean, 3),
            "attack_score_mean_norm": round(self._clamp_0_1((attack_score_mean - 1.0) / 9.0), 3),
            "attack_score_max": max(attack_scores),
            "attack_probability_mean": round(self._mean(attack_probability_values), 3),

            # Toxizität
            "toxic_count": sum(toxic_flags),
            "toxic_ratio": round(sum(toxic_flags) / comment_count, 3),
            "toxicity_score_mean": round(toxicity_score_mean, 3),
            "toxicity_score_mean_norm": round(self._clamp_0_1((toxicity_score_mean - 1.0) / 3.0), 3),
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
            "imperative_mean": round(self._mean(imperative_counts), 3),
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

            # ML-Rollenwahrscheinlichkeiten als weiche Zusatz-/Debugsignale
            "counter_speech_probability_mean": round(self._mean(counter_speech_probability_values), 3),
            "target_response_probability_mean": round(self._mean(target_response_probability_values), 3),
            "deescalation_probability_mean": round(self._mean(deescalation_probability_values), 3),

            # Erklärung / Debug, nicht Hauptscore
            "irony_mean": round(self._mean(irony_values), 3),
            "reply_depth_mean": round(self._mean(reply_depth_values), 3),
            "reply_depth_max": max(reply_depth_values),
            "num_children_mean": round(self._mean(num_children_values), 3),
        }
