"""Warnstufen-Policy für das Shitstorm-Barometer."""

from __future__ import annotations

from typing import Dict

from .models import DimensionResult, WarningLevel


class WarningLevelPolicy:
    """Leitet Warnstufen aus Barometer und Dimensionsscores ab.
    """

    def __init__(
        self,
        watch_threshold: float = 0.20,
        warning_threshold: float = 0.40,
        critical_threshold: float = 0.60,
    ):
        self.watch_threshold = watch_threshold
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    def decide(self, barometer_score: float, dimensions: Dict[str, DimensionResult]) -> str:
        frequency = dimensions["frequency"].evidence_score
        aggression = dimensions["aggression_toxicity"].evidence_score
        dynamics = dimensions["dynamics"].evidence_score
        focus = dimensions["focus_personalization"].evidence_score

        has_core = frequency >= self.watch_threshold and aggression >= self.watch_threshold
        has_strong_core = frequency >= self.warning_threshold and aggression >= self.warning_threshold
        has_support = dynamics >= self.watch_threshold or focus >= self.watch_threshold

        if barometer_score >= self.critical_threshold and has_strong_core and has_support:
            return WarningLevel.CRITICAL.value

        if barometer_score >= self.warning_threshold and has_core:
            return WarningLevel.WARNING.value

        if barometer_score >= self.watch_threshold or any(
            value >= self.watch_threshold for value in [frequency, aggression, dynamics, focus]
        ):
            return WarningLevel.WATCH.value

        return WarningLevel.NORMAL.value
