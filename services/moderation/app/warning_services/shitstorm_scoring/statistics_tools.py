"""Statistische Hilfsklassen für das Shitstorm-Barometer.

Hier liegen die p-Wert-Berechnung, p-Wert-Kombination und Transformation
in normierte Evidenzscores. 
"""

from __future__ import annotations

import math
from typing import Iterable, List

from .models import DimensionCombiner, PValueMethod


class PValueCalculator:
    """Berechnet obere p-Werte.

    Kleine p-Werte bedeuten: Der aktuelle Wert ist im Vergleich zur bisherigen
    Thread-Historie auffällig hoch.
    """

    def __init__(self, min_history: int = 3, poisson_baseline_floor: float = 0.1):
        self.min_history = min_history
        self.poisson_baseline_floor = poisson_baseline_floor

    def calculate(
        self,
        method: PValueMethod,
        current_value: float,
        previous_values: List[float],
    ) -> float:
        if len(previous_values) < self.min_history:
            # Zu wenig Historie: konservativ keine Auffälligkeit behaupten.
            return 1.0

        if method == "poisson":
            return self._poisson_upper_tail(current_value, previous_values)

        if method == "empirical":
            return self._empirical_upper_tail(current_value, previous_values)

        raise ValueError(f"Unknown p-value method: {method}")

    def _poisson_upper_tail(self, current_value: float, previous_values: List[float]) -> float:
        """P(X >= current_value) bei X ~ Poisson(lambda_baseline)."""
        current_count = max(0, int(round(current_value)))
        if current_count <= 0:
            return 1.0

        baseline_lambda = sum(previous_values) / len(previous_values)
        baseline_lambda = max(baseline_lambda, self.poisson_baseline_floor)

        return self._poisson_survival_function(k=current_count, lam=baseline_lambda)

    @staticmethod
    def _empirical_upper_tail(current_value: float, previous_values: List[float]) -> float:
        """Empirischer oberer p-Wert mit +1-Korrektur."""
        at_least_as_extreme = sum(1 for value in previous_values if value >= current_value)
        return (at_least_as_extreme + 1) / (len(previous_values) + 1)

    @staticmethod
    def _poisson_survival_function(k: int, lam: float) -> float:
        """Survival Function P(X >= k) ohne SciPy-Abhängigkeit."""
        if k <= 0:
            return 1.0

        try:
            probability_zero = math.exp(-lam)
        except OverflowError:
            return 0.0

        cumulative = probability_zero
        probability_i = probability_zero

        # cumulative = P(X <= k - 1)
        for i in range(1, k):
            probability_i *= lam / i
            cumulative += probability_i

        survival = 1.0 - cumulative
        return min(1.0, max(0.0, survival))

"""Nur für Testzwecke"""
class PValueCombiner:
    """Kombiniert mehrere Indikator-p-Werte innerhalb einer Dimension.

    Diese Klasse wird für Bonferroni/Fisher genutzt. Für den Mean-Combiner
    werden nicht p-Werte gemittelt, sondern Evidenzscores im Scorer.
    """

    def __init__(self, method: DimensionCombiner = "bonferroni"):
        self.method = method

    def combine(self, p_values: Iterable[float]) -> float:
        clean_values = [self._clip_p(value) for value in p_values]
        if not clean_values:
            return 1.0

        if self.method == "bonferroni":
            return self._bonferroni(clean_values)

        if self.method == "fisher":
            return self._fisher(clean_values)

        raise ValueError(
            f"PValueCombiner cannot combine p-values with method '{self.method}'. "
            "Use method='bonferroni' or method='fisher'."
        )

    @staticmethod
    def _clip_p(p_value: float) -> float:
        return min(1.0, max(1e-12, float(p_value)))

    @staticmethod
    def _bonferroni(p_values: List[float]) -> float:
        """Konservative Kombination: k * kleinster p-Wert, gedeckelt bei 1."""
        return min(1.0, len(p_values) * min(p_values))

    @staticmethod
    def _fisher(p_values: List[float]) -> float:
        """Fisher-Kombination als optionale Sensitivitätsanalyse.
        """
        try:
            from scipy.stats import chi2  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Fisher combiner requires scipy. Use 'mean' or 'bonferroni' instead.") from exc

        statistic = -2.0 * sum(math.log(value) for value in p_values)
        degrees_of_freedom = 2 * len(p_values)
        return float(chi2.sf(statistic, degrees_of_freedom))


class EvidenceTransformer:
    """Transformiert p-Werte in Evidenzscores zwischen 0 und 1."""

    def __init__(self, p_value_for_full_evidence: float = 0.01):
        if not 0 < p_value_for_full_evidence < 1:
            raise ValueError("p_value_for_full_evidence must be between 0 and 1.")
        self.denominator = -math.log10(p_value_for_full_evidence)

    def transform(self, p_value: float) -> float:
        p_value = min(1.0, max(1e-12, float(p_value)))
        evidence = -math.log10(p_value) / self.denominator
        return min(1.0, max(0.0, evidence))
