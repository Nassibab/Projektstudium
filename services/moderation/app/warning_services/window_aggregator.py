from collections import Counter

#berechnet aus MEHREREN Kommentaren EINES Fensters zusammenfassende Werte. 
#reine Messwerte.

class WindowAggregator:
    def __init__(self, window_store):
        self.window_store = window_store

    def _to_float(self, value, default=0.0):
        try:
            if value is None:
                return default
            return float(value)
        except (ValueError, TypeError):
            return default

    def _to_int(self, value, default=0):
        try:
            if value is None:
                return default
            return int(value)
        except (ValueError, TypeError):
            return default

    def _mean(self, values):
        values = [v for v in values if v is not None]
        return sum(values) / len(values) if values else 0
    
     
     #Funktion nimmt ein bestimmtes Zeitfenster + Thread und berechnet daraus Kennzahlen
    def aggregate(self, thread_id, window_start):
        comments = self.window_store.get_comments(thread_id, window_start)
        comment_count = len(comments)

        users = [c.get("login") for c in comments if c.get("login")]
        user_counts = Counter(users)

        unique_users = len(user_counts)
        max_user_comments = max(user_counts.values()) if user_counts else 0
        dominant_user_ratio = max_user_comments / comment_count if comment_count else 0


        #
        is_attacking_values = [
            self._to_int(c.get("is_attacking"), 0)
            for c in comments
        ]

        attack_scores = [
            self._to_float(c.get("attack_score"), 1)
            for c in comments
        ]

        toxicity_scores = [
            self._to_float(c.get("toxicity_score"), 1)
            for c in comments
        ]

        insult_counts = [
            self._to_float(c.get("insult_count"), 0)
            for c in comments
        ]

        swearword_counts = [
            self._to_float(c.get("swearword_count"), 0)
            for c in comments
        ]

        negative_word_counts = [
            self._to_float(c.get("negative_word_count"), 0)
            for c in comments
        ]

        direct_address_counts = [
            self._to_float(c.get("direct_address_count"), 0)
            for c in comments
        ]

        accusation_marker_counts = [
            self._to_float(c.get("accusation_marker_count"), 0)
            for c in comments
        ]

        mockery_marker_counts = [
            self._to_float(c.get("mockery_marker_count"), 0)
            for c in comments
        ]

        irony_values = [
            self._to_float(c.get("irony"), 0)
            for c in comments
        ]

        attack_streak_values = [
            self._to_float(c.get("attack_streak_current"), 0)
            for c in comments
        ]

        recent_attack_rate_3_values = [
            self._to_float(c.get("recent_attack_rate_3"), 0)
            for c in comments
        ]

        recent_attack_rate_5_values = [
            self._to_float(c.get("recent_attack_rate_5"), 0)
            for c in comments
        ]

        target_recently_attacked_values = [
            self._to_int(c.get("target_recently_attacked"), 0)
            for c in comments
        ]

        reply_after_attack_values = [
            self._to_int(c.get("reply_after_attack"), 0)
            for c in comments
        ]

        reply_depth_values = [
            self._to_float(c.get("reply_depth"), 0)
            for c in comments
        ]

        num_children_values = [
            self._to_float(c.get("num_children"), 0)
            for c in comments
        ]

        attack_count = sum(1 for v in is_attacking_values if v == 1)
        toxic_count = sum(1 for v in toxicity_scores if v >= 4)
        insult_comment_count = sum(1 for v in insult_counts if v > 0)
        swearword_comment_count = sum(1 for v in swearword_counts if v > 0)

        return {
            "thread_id": thread_id,
            "window_start": window_start.isoformat(),
            "window_end": self.window_store.get_window_end(window_start).isoformat(),

            # Activity
            "comment_count": comment_count,
            "unique_users": unique_users,
            "dominant_user_ratio": round(dominant_user_ratio, 3),

            # Aggression
            "attack_count": attack_count,
            "attack_ratio": round(attack_count / comment_count, 3) if comment_count else 0,
            "attack_score_mean": round(self._mean(attack_scores), 3),
            "attack_score_max": max(attack_scores) if attack_scores else 0,

            # Toxicity
            "toxic_count": toxic_count,
            "toxic_ratio": round(toxic_count / comment_count, 3) if comment_count else 0,
            "toxicity_score_mean": round(self._mean(toxicity_scores), 3),
            "toxicity_score_max": max(toxicity_scores) if toxicity_scores else 0,

            # Insults / negative language
            "insult_comment_count": insult_comment_count,
            "insult_ratio": round(insult_comment_count / comment_count, 3) if comment_count else 0,
            "insult_count_sum": sum(insult_counts),
            "swearword_comment_count": swearword_comment_count,
            "swearword_ratio": round(swearword_comment_count / comment_count, 3) if comment_count else 0,
            "negative_word_count_mean": round(self._mean(negative_word_counts), 3),

            # Personalization / conflict markers
            "direct_address_mean": round(self._mean(direct_address_counts), 3),
            "accusation_marker_mean": round(self._mean(accusation_marker_counts), 3),
            "mockery_marker_mean": round(self._mean(mockery_marker_counts), 3),
            "irony_mean": round(self._mean(irony_values), 3),

            # Escalation dynamics from Analyse-R
            "attack_streak_max": max(attack_streak_values) if attack_streak_values else 0,
            "recent_attack_rate_3_mean": round(self._mean(recent_attack_rate_3_values), 3),
            "recent_attack_rate_5_mean": round(self._mean(recent_attack_rate_5_values), 3),
            "target_recently_attacked_ratio": round(sum(target_recently_attacked_values) / comment_count, 3) if comment_count else 0,
            "reply_after_attack_ratio": round(sum(reply_after_attack_values) / comment_count, 3) if comment_count else 0,

            # Thread interaction structure
            "reply_depth_mean": round(self._mean(reply_depth_values), 3),
            "reply_depth_max": max(reply_depth_values) if reply_depth_values else 0,
            "num_children_mean": round(self._mean(num_children_values), 3),
        }