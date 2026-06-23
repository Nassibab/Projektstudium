"""Historie vergangener 5-Minuten-Fenster je Thread."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from .models import SafeNumber


class ThreadMetricHistory:
    """Speichert bereits ausgewertete Fensterwerte pro Thread.

    Der Scorer darf für das aktuelle Fenster nur die Vergangenheit kennen.
    Deshalb werden aktuelle Metriken erst nach der Score-Berechnung angehängt.
    """

    def __init__(self, history_window_size: int = 5):
        self.history_window_size = history_window_size
        self._history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def previous_metric_values(self, thread_id: str, metric_name: str) -> List[float]:
        windows = self._history[thread_id][-self.history_window_size:]
        return [SafeNumber.to_float(window.get(metric_name, 0.0)) for window in windows]

    def previous_barometer_values(self, thread_id: str) -> List[float]:
        windows = self._history[thread_id][-self.history_window_size:]
        return [SafeNumber.to_float(window.get("shitstorm_barometer", 0.0)) for window in windows]

    def append(self, thread_id: str, metrics: Dict[str, Any]) -> None:
        self._history[thread_id].append(dict(metrics))
