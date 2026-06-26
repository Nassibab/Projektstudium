"""Statistische Hilfsklassen für das Shitstorm-Barometer.

Neues Verfahren:
- Jeder Indikator wird gegen seine Rolling-Historie desselben Threads geprüft.
- Der positive Rolling-z-Score erkennt abrupte Ausschläge.
- Ein einseitiges CUSUM erkennt langsam auflaufende Eskalation über mehrere Fenster.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class RollingSignalResult:
    """Debug- und Scorewerte für einen einzelnen Indikator."""

    evidence_score: float
    rolling_mean: Optional[float]
    rolling_std: Optional[float]
    z_score: float
    z_evidence_score: float
    cusum_value: float
    cusum_evidence_score: float
    has_sufficient_history: bool
    insufficient_history_message: Optional[str] = None
    method: str = "rolling_z_cusum"


class RollingZCusumDetector:
    """Berechnet Evidenz aus Rolling-z-Score und einseitigem CUSUM.

    Intuition:
    - z_score hoch: aktuelles Fenster liegt deutlich über der eigenen
      Thread-Vergangenheit.
    - CUSUM hoch: mehrere Fenster in Folge liegen moderat über der Baseline.

    evidence_score = max(z_evidence_score, cusum_evidence_score)
    Dadurch reagieren wir sowohl auf plötzliche Peaks als auch auf langsame
    Shitstorm-Eskalationen.
    """

    def __init__(
        self,
        min_history: int = 3,
        z_watch: float = 1.0,
        z_full: float = 3.0,
        cusum_reference: float = 0.5,
        cusum_watch: float = 1.5,
        cusum_full: float = 5.0,
    ):
        if min_history < 1:
            raise ValueError("min_history must be >= 1")
        if z_full <= z_watch:
            raise ValueError("z_full must be greater than z_watch")
        if cusum_full <= cusum_watch:
            raise ValueError("cusum_full must be greater than cusum_watch")
        if cusum_reference < 0:
            raise ValueError("cusum_reference must be >= 0")

        self.min_history = min_history
        self.z_watch = z_watch
        self.z_full = z_full
        self.cusum_reference = cusum_reference
        self.cusum_watch = cusum_watch
        self.cusum_full = cusum_full

    def calculate(
        self,
        current_value: float,
        previous_values: List[float],
        previous_cusum: float = 0.0,
    ) -> RollingSignalResult:
        previous_cusum = max(0.0, float(previous_cusum or 0.0))

        if len(previous_values) < self.min_history:
            # Zu wenig Historie für eine wissenschaftlich saubere relative Aussage.
            # Es gibt bewusst keinen absoluten Ersatzscore. Das Ergebnis bleibt
            # vorläufig und fließt mit Evidenz 0 in das Barometer ein.
            return RollingSignalResult(
                evidence_score=0.0,
                rolling_mean=None,
                rolling_std=None,
                z_score=0.0,
                z_evidence_score=0.0,
                cusum_value=0.0,
                cusum_evidence_score=0.0,
                has_sufficient_history=False,
                insufficient_history_message=(
                    f"Noch nicht genug Vergleichsfenster: "
                    f"{len(previous_values)}/{self.min_history}."
                ),
            )

        rolling_mean = self._mean(previous_values)
        rolling_std = max(
            self._sample_std(previous_values, rolling_mean),
            self._adaptive_std_floor(current_value, previous_values),
        )

        z_score = (current_value - rolling_mean) / rolling_std

        # Einseitiges positives CUSUM. Negative/kleine z-Werte bauen das Signal ab.
        cusum_value = max(0.0, previous_cusum + z_score - self.cusum_reference)

        z_evidence = self._z_to_evidence(z_score)
        cusum_evidence = self._cusum_to_evidence(cusum_value)

        return RollingSignalResult(
            evidence_score=max(z_evidence, cusum_evidence),
            rolling_mean=rolling_mean,
            rolling_std=rolling_std,
            z_score=z_score,
            z_evidence_score=z_evidence,
            cusum_value=cusum_value,
            cusum_evidence_score=cusum_evidence,
            has_sufficient_history=True,
            insufficient_history_message=None,
        )

    @staticmethod
    def _mean(values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def _sample_std(values: List[float], mean: float) -> float:
        if len(values) < 2:
            return 0.0
        variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
        return math.sqrt(max(0.0, variance))

    @staticmethod
    def _clip01(value: float) -> float:
        return min(1.0, max(0.0, float(value)))

    def _z_to_evidence(self, z_score: float) -> float:
        return self._clip01((z_score - self.z_watch) / (self.z_full - self.z_watch))

    def _cusum_to_evidence(self, cusum_value: float) -> float:
        return self._clip01((cusum_value - self.cusum_watch) / (self.cusum_full - self.cusum_watch))

    @staticmethod
    def _adaptive_std_floor(current_value: float, previous_values: List[float]) -> float:
        """Verhindert explodierende z-Werte bei fast konstanter Historie.
        """
        values = [float(current_value), *[float(value) for value in previous_values]]
        min_value = min(values)
        max_value = max(values)

        if 0.0 <= min_value and max_value <= 1.0:
            return 0.05

        if 0.0 <= min_value and max_value <= 4.0:
            return 0.25

        return 1.0
