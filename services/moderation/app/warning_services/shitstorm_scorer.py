from collections import defaultdict
import statistics


class ShitstormScorer:
    def __init__(self, history_window_size=5):
        self.thread_history = defaultdict(list)
        self.history_window_size = history_window_size
        self.cusum_values = defaultdict(float)

        self.metric_groups = {
            "activity": ["comment_count", "unique_users"],
            "aggression": ["attack_ratio", "attack_score_mean", "insult_ratio"],
            "toxicity": ["toxic_ratio", "toxicity_score_mean"],
            "personalization": [
                "direct_address_mean",
                "target_recently_attacked_ratio",
                "reply_after_attack_ratio"
            ],
            "escalation_dynamics": [
                "recent_attack_rate_5_mean",
                "attack_streak_max"
            ]
        }

    def safe_get(self, metrics, key, default=0.0):
        try:
            value = metrics.get(key, default)
            return default if value is None else float(value)
        except (ValueError, TypeError):
            return default

    def get_previous_values(self, thread_id, metric_name):
        return [
            self.safe_get(h, metric_name)
            for h in self.thread_history[thread_id][-self.history_window_size:]
        ]

    def calculate_z_score(self, thread_id, metric_name, current_value):
        previous_values = self.get_previous_values(thread_id, metric_name)

        if len(previous_values) < 3:
            return 0.0

        mean_value = statistics.mean(previous_values)
        std_value = statistics.pstdev(previous_values)

        if std_value == 0:
            return 3.0 if current_value > mean_value else 0.0

        return (current_value - mean_value) / std_value

    def calculate_cusum(self, thread_id, metric_name, current_value):
        previous_values = self.get_previous_values(thread_id, metric_name)

        if len(previous_values) < 3:
            return 0.0

        expected_mean = statistics.mean(previous_values)
        std_value = statistics.pstdev(previous_values)

        # Datengetriebener Drift:
        # Normale kleine Schwankungen werden ignoriert.
        drift = std_value * 0.5

        # CUSUM wird pro Thread UND pro Metrik gespeichert. ("ThreadX", "attack_ratio")
        key = (thread_id, metric_name)
        
        # Positive Abweichung vom erwarteten Mittelwert.
        increase = current_value - expected_mean - drift
        
        # CUSUM kann nicht negativ werden.
        self.cusum_values[key] = max(0.0, self.cusum_values[key] + increase)

        return self.cusum_values[key]

    # Einfache Trend-Erkennung: 
    # Prüft, ob die letzten drei Werte streng steigen.# 0.1 --> 0.2 --> 0.4
    def calculate_trend_detected(self, thread_id, metric_name, current_value):
        values = self.get_previous_values(thread_id, metric_name)
        values.append(current_value)

        if len(values) < 4:
            return False

        return values[-1] > values[-2] > values[-3]

    def scale_z_to_score(self, z_score):
        """
        Converts z-score to 0-100.
        z <= 0 -> 0
        z >= 3 -> 100
        """
        return round(min(max(z_score, 0), 3) / 3 * 100, 2)

    """
    Prüft eine einzelne Metrik mit drei statistischen Verfahren:
    - Rolling Z-Score
    - CUSUM
    - Trendanalyse
    """
    def analyze_metric(self, thread_id, metric_name, current_value):
        z_score = self.calculate_z_score(thread_id, metric_name, current_value)
        cusum = self.calculate_cusum(thread_id, metric_name, current_value)
        trend_detected = self.calculate_trend_detected(thread_id, metric_name, current_value)

        metric_score = self.scale_z_to_score(z_score)

        return {
            "current_value": current_value,
            "z_score": round(z_score, 3),
            "cusum": round(cusum, 3),
            "cusum_signal": cusum >= 3,
            "trend_signal": trend_detected
        }
    
    """
    Prüft eine fachliche Eskalationsdimension.
    Beispiel:
    Dimension 'aggression' besteht aus:
    attack_ratio, attack_score_mean, insult_ratio

    Die Dimension ist auffällig, wenn mindestens eine ihrer Metriken
    ein statistisches Signal auslöst.
    """
    def analyze_dimension(self, thread_id, metrics, dimension_name, metric_names):
        metric_results = {}

        for metric_name in metric_names:
            current_value = self.safe_get(metrics, metric_name)
            metric_results[metric_name] = self.analyze_metric(
                thread_id,
                metric_name,
                current_value
            )

        metric_scores = [
            result["metric_score"]
            for result in metric_results.values()
        ]

        dimension_score = (
            statistics.mean(metric_scores)
            if metric_scores
            else 0.0
        )

        dimension_alert = any(
            result["z_score"] >= 2
            or result["cusum"] >= 3
            or result["trend_signal"]
            for result in metric_results.values()
        )

        return {
            "dimension": dimension_name,
            "dimension_score": round(dimension_score, 2),
            "alert": dimension_alert,
            "metric_results": metric_results
        }
       
    """
    Hauptfunktion.
    Bewertet nicht einzelne Variablen direkt,
    sondern mehrere Eskalationsdimensionen.
    """
    def calculate_final_score(self, thread_id, metrics):
        dimension_results = {}

        for dimension_name, metric_names in self.metric_groups.items():
            dimension_results[dimension_name] = self.analyze_dimension(
                thread_id,
                metrics,
                dimension_name,
                metric_names
            )

        dimension_scores = {
            name: result["dimension_score"]
            for name, result in dimension_results.items()
        }

        # Finales Shitstorm-Barometer: Durchschnitt der Eskalationsdimensionen
        shitstorm_barometer = (
            statistics.mean(dimension_scores.values())
            if dimension_scores
            else 0.0
        )

        warning_level = self.get_warning_level_from_dimensions(dimension_results)

        metrics["shitstorm_barometer"] = round(shitstorm_barometer, 2)
        metrics["warning_level"] = warning_level
        metrics["dimension_scores"] = dimension_scores

        self.thread_history[thread_id].append(metrics)

        return {
            "thread_id": thread_id,
            "shitstorm_barometer": round(shitstorm_barometer, 2),
            "warning_level": warning_level,
            "dimension_scores": dimension_scores,
            "dimension_results": dimension_results,
            "recent_barometer_values": [
                h.get("shitstorm_barometer", 0)
                for h in self.thread_history[thread_id][-self.history_window_size:]
            ]
        }
        
        """
        Warnlogik auf Dimensionsebene.
        Dadurch wird verhindert, dass eine einzelne Dimension,
        z. B. nur Aktivität, sofort eine starke Warnung auslöst.
        """
    def get_warning_level_from_dimensions(self, dimension_results):
        alerted = [
            name
            for name, result in dimension_results.items()
            if result["alert"]
        ]

        has_activity = "activity" in alerted
        has_aggression = "aggression" in alerted
        has_toxicity = "toxicity" in alerted
        has_personalization = "personalization" in alerted
        has_escalation = "escalation_dynamics" in alerted

        # Critical:
        # Mehrere Kernbereiche schlagen gleichzeitig an.
        if (
            has_activity
            and (has_aggression or has_toxicity)
            and (has_personalization or has_escalation)
        ):
            return "critical"

        # Warning:
        # Mindestens zwei relevante Dimensionen auffällig,
        # darunter Aggression oder Toxizität.
        if (
            len(alerted) >= 2
            and (has_aggression or has_toxicity)
        ):
            return "warning"

        # Watch:
        # Erste statistische Auffälligkeit vorhanden.
        if len(alerted) >= 1:
            return "watch"

        return "normal"