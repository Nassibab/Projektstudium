"""Warnstufen-Policy für das Shitstorm-Barometer.

Mit Aggressions-Cap:
- Der Barometerwert ist bereits durch Aggression/Toxizität/Negativität begrenzt.
- Deshalb wird Aggression in der Warnstufe nicht erneut als Kernbedingung geprüft.
- Die Warnstufe wird über transparente, kalibrierbare Barometer-Schwellen abgeleitet.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .models import DimensionResult, WarningLevel


class WarningLevelPolicy:
    """Leitet handlungsorientierte Warnstufen aus dem finalen Barometerwert ab.

    Die Schwellen sind Kalibrierparameter:
    - watch_threshold: Beobachtungsbereich
    - warning_threshold: deutliche Eskalation
    - critical_threshold: starke Eskalation

    Der Score selbst enthält durch Score_final = min(Score_raw, Aggression) bereits
    die inhaltliche Kernbedingung. Daher bleibt die Policy bewusst einfach.
    """

    def __init__(
        self,
        watch_threshold: float = 0.20,
        warning_threshold: float = 0.40,
        critical_threshold: float = 0.60,
    ):
        if not 0.0 <= watch_threshold <= warning_threshold <= critical_threshold <= 1.0:
            raise ValueError(
                "Expected 0 <= watch_threshold <= warning_threshold <= critical_threshold <= 1."
            )

        self.watch_threshold = watch_threshold
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    def decide(
        self,
        barometer_score: float,
        dimensions: Optional[Dict[str, DimensionResult]] = None,
    ) -> str:
        """Rückwärtskompatible Kurzform."""
        return self.evaluate(barometer_score, dimensions)["warning_level"]

    def evaluate(
        self,
        barometer_score: float,
        dimensions: Optional[Dict[str, DimensionResult]] = None,
    ) -> Dict[str, Any]:
        score = min(1.0, max(0.0, float(barometer_score)))

        if score >= self.critical_threshold:
            level = WarningLevel.CRITICAL.value
            reason = "barometer_ge_critical_threshold"
        elif score >= self.warning_threshold:
            level = WarningLevel.WARNING.value
            reason = "barometer_ge_warning_threshold"
        elif score >= self.watch_threshold:
            level = WarningLevel.WATCH.value
            reason = "barometer_ge_watch_threshold"
        else:
            level = WarningLevel.NORMAL.value
            reason = "barometer_below_watch_threshold"

        dimension_values: Dict[str, float] = {}
        if dimensions:
            dimension_values = {
                name: round(result.evidence_score, 4)
                for name, result in dimensions.items()
            }

        return {
            "warning_level": level,
            "reason": reason,
            "barometer_score": round(score, 4),
            "thresholds": {
                "watch_threshold": self.watch_threshold,
                "warning_threshold": self.warning_threshold,
                "critical_threshold": self.critical_threshold,
            },
            "dimension_values": dimension_values,
        }
