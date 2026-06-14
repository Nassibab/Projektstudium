from collections import defaultdict
import statistics

#kein frei gewichteteter window_score.
#Der Score entsteht nur noch daraus, wie viele statistische Warnsignale anschlagen.

class ShitstormScorer:
    def __init__(self, history_window_size=5):
        # Speichert pro Thread die vergangenen aggregierten Zeitfenster.        # {
        #   "Thread X": [
        #       {"comment_count": 5, "attack_ratio": 0.1, ...},
        #       {"comment_count": 8, "attack_ratio": 0.2, ...}
        #   ]
        # }
        self.thread_history = defaultdict(list)

        # Anzahl der vergangenen Fenster, die für Vergleiche verwendet werden.
        self.history_window_size = history_window_size

        ## Speichert CUSUM-Werte je Thread und Metrik.
        self.cusum_values = defaultdict(float)

        # Diese aggregierten Metriken werden überwacht.
        self.monitored_metrics = [
            "comment_count",
            "unique_users",
            "attack_ratio",
            "toxic_ratio",
            "attack_score_mean",
            "toxicity_score_mean",
            "insult_ratio",
            "direct_address_mean",
            "recent_attack_rate_5_mean",
            "target_recently_attacked_ratio",
            "reply_after_attack_ratio",
            "attack_streak_max"
        ]

    ## Falls der Wert fehlt oder None ist, wird 0.0 verwendet.
    def safe_get(self, metrics, key, default=0.0):
        value = metrics.get(key, default)
        return default if value is None else float(value)
    


    # Rolling Z-Score:
    # Vergleicht den aktuellen Wert mit den vorherigen Fenstern desselben Threads.
    def calculate_z_score(self, thread_id, metric_name, current_value):
        history = self.thread_history[thread_id]

        # Nimm nur die letzten n Fenster.
        previous_values = [
            self.safe_get(h, metric_name)
            for h in history[-self.history_window_size:]
        ]

        # Mindestens 3 Vergleichswerte nötig.
        # Sonst ist der Z-Score statistisch wenig sinnvoll.
        if len(previous_values) < 3:
            return 0.0
        
        #Durchschnitt und Standarabweichung
        mean_value = statistics.mean(previous_values)
        std_value = statistics.pstdev(previous_values)

        # Wenn keine Streuung vorhanden ist: 
        if std_value == 0:
            # Wenn der aktuelle Wert größer ist als der bisherige Mittelwert,
            # wird künstlich ein starkes Signal gesetzt.
            return 3.0 if current_value > mean_value else 0.0
        
        # Standardformel: z = (aktueller Wert - Mittelwert) / Standardabweichung
        return (current_value - mean_value) / std_value



    # CUSUM: Erkennt schleichende Eskalationen.
    # Anders als der Z-Score erkennt CUSUM nicht nur einzelne große Ausreißer,
    # sondern summiert mehrere kleine positive Abweichungen über Zeit auf.
    def calculate_cusum(self, thread_id, metric_name, current_value):
        history = self.thread_history[thread_id]

        previous_values = [
            self.safe_get(h, metric_name)
            for h in history[-self.history_window_size:]
        ]

        # mindestens 3 Vergleichsfenster nötig.
        if len(previous_values) < 3:
            return 0.0

        expected_mean = statistics.mean(previous_values)
        std_value = statistics.pstdev(previous_values)

        # datengetriebener drift: kleine normale Schwankungen werden ignoriert
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
        history = self.thread_history[thread_id]

        values = [
            self.safe_get(h, metric_name)
            for h in history[-self.history_window_size:]
        ]

        values.append(current_value)

        if len(values) < 4:
            return False

        return values[-1] > values[-2] > values[-3]




    # Zentrale Funktion: Sie berechnet den Shitstorm-Score für das aktuelle Zeitfenster.
    def calculate_final_score(self, thread_id, metrics):
        signals = []
        details = {}

        for metric_name in self.monitored_metrics:
            current_value = self.safe_get(metrics, metric_name)

            # 1. Z-Score berechnen
            z_score = self.calculate_z_score(
                thread_id,
                metric_name,
                current_value
            )

            # 2. CUSUM berechnen
            cusum = self.calculate_cusum(
                thread_id,
                metric_name,
                current_value
            )

            # 3. Trend prüfen
            trend_detected = self.calculate_trend_detected(
                thread_id,
                metric_name,
                current_value
            )
            
            # Statistische Warnsignale:
            # z_score >= 2 bedeutet: aktueller Wert liegt deutlich über dem bisherigen Normalbereich.
            z_signal = z_score >= 2

            # cusum >= 3 bedeutet: über mehrere Fenster wurde eine kumulative Abweichung aufgebaut.
            cusum_signal = cusum >= 3

            # Trend-Signal: die letzten Werte steigen kontinuierlich.
            trend_signal = trend_detected

            details[metric_name] = {
                "current_value": current_value,
                "z_score": round(z_score, 3),
                "z_signal": z_signal,
                "cusum": round(cusum, 3),
                "cusum_signal": cusum_signal,
                "trend_signal": trend_signal
            }

            # Wenn ein Signal auslöst, wird es gezählt.
            if z_signal:
                signals.append(f"{metric_name}:z_score")

            if cusum_signal:
                signals.append(f"{metric_name}:cusum")

            if trend_signal:
                signals.append(f"{metric_name}:trend")

        # Jede Metrik kann maximal 3 Signale erzeugen:
        # Z-Score, CUSUM, Trend
        max_possible_signals = len(self.monitored_metrics) * 3

        # Finaler Score:
        # Anteil der ausgelösten Signale an allen möglichen Signalen.
        #
        # Beispiel: 6 Signale von 36 möglichen:
        # 6 / 36 * 100 = 16.67
        final_score = (len(signals) / max_possible_signals) * 100

        # Aktuelles Fenster inklusive Score speichern.
        # Das ist wichtig, damit spätere Fenster eine Historie haben.
        metrics["final_shitstorm_score"] = round(final_score, 2)
        metrics["triggered_signals"] = signals

        self.thread_history[thread_id].append(metrics)

        return {
            "thread_id": thread_id,
            "final_shitstorm_score": round(final_score, 2),
            "warning_level": self.get_warning_level(final_score),
            "triggered_signal_count": len(signals),
            "max_possible_signals": max_possible_signals,
            "triggered_signals": signals,
            "signal_details": details,
            "recent_scores": [
                h.get("final_shitstorm_score", 0)
                for h in self.thread_history[thread_id][-self.history_window_size:]
            ]
        }

    def get_warning_level(self, score):
        if score >= 50:
            return "critical"
        if score >= 25:
            return "warning"
        if score >= 10:
            return "watch"
        return "normal"