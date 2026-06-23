
"""Historie vergangener 5-Minuten-Fenster je Thread."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from .models import SafeNumber


class ThreadMetricHistory:
    """Speichert ausgewertete Fensterwerte pro Thread.

    Wichtig für Live-/Kommentar-für-Kommentar-Auswertung:
    Ein 5-Minuten-Fenster kann durch jeden neu eintreffenden Kommentar erneut
    aggregiert werden. Deshalb darf dasselbe Fenster nicht mehrfach in der
    Historie landen. Stattdessen wird der vorhandene Eintrag für dieses Fenster
    ersetzt.

    Für p-Werte wird außerdem das aktuelle Fenster aus der Vergleichshistorie
    ausgeschlossen. Der aktuelle Fensterzustand soll nur mit früheren Fenstern
    verglichen werden, nicht mit früheren Zwischenständen desselben Fensters.
    """

    def __init__(self, history_window_size: int = 5):
        self.history_window_size = history_window_size
        self._history: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)

    @staticmethod
    def _same_window(left: Any, right: Any) -> bool:
        return str(left) == str(right)

    def _previous_windows(
        self,
        thread_id: Any,
        current_window_start: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        windows = self._history[thread_id]

        if current_window_start is not None:
            windows = [
                window for window in windows
                if not self._same_window(window.get("window_start"), current_window_start)
            ]

        return windows[-self.history_window_size:]

    def previous_metric_values(
        self,
        thread_id: Any,
        metric_name: str,
        current_window_start: Optional[Any] = None,
    ) -> List[float]:
        windows = self._previous_windows(thread_id, current_window_start)
        return [SafeNumber.to_float(window.get(metric_name, 0.0)) for window in windows]

    def previous_barometer_values(
        self,
        thread_id: Any,
        current_window_start: Optional[Any] = None,
    ) -> List[float]:
        windows = self._previous_windows(thread_id, current_window_start)
        return [SafeNumber.to_float(window.get("shitstorm_barometer", 0.0)) for window in windows]

    def upsert(self, thread_id: Any, metrics: Dict[str, Any]) -> None:
        """Speichert ein Fenster oder ersetzt den vorhandenen Eintrag desselben Fensters."""
        current_window_start = metrics.get("window_start")

        history = [
            window for window in self._history[thread_id]
            if not self._same_window(window.get("window_start"), current_window_start)
        ]

        history.append(dict(metrics))

        # Eine  zusätzliche Position behalten, weil das aktuelle Fenster bei
        # der nächsten Bewertung aus der Vergleichshistorie ausgeschlossen wird.
        # So bleiben trotz aktuellem Fenster noch history_window_size frühere
        # Fenster für p-Werte verfügbar.
        self._history[thread_id] = history[-(self.history_window_size + 1):]

    def append(self, thread_id: Any, metrics: Dict[str, Any]) -> None:
        """Rückwärtskompatibler Alias: nutzt bewusst upsert statt blindem Anhängen."""
        self.upsert(thread_id, metrics)
