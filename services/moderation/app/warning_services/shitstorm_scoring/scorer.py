"""Hauptlogik für das Shitstorm-Barometer."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, List, Optional

from .config import DEFAULT_DIMENSIONS
from .history import ThreadMetricHistory
from .models import (
    DimensionCombiner,
    DimensionResult,
    DimensionSpec,
    IndicatorResult,
    IndicatorSpec,
    SafeNumber,
)
from .policy import WarningLevelPolicy
from .statistics_tools import EvidenceTransformer, PValueCalculator, PValueCombiner


class ShitstormScorer:
    """Berechnet ein Shitstorm-Barometer als Composite Indicator.

    Methodik im Hauptmodell `dimension_combiner="mean"`:
    1. Pro Indikator wird ein p-Wert berechnet.
    2. Jeder p-Wert wird in einen Evidenzscore von 0 bis 1 transformiert.
    3. Innerhalb einer Dimension wird ein hierarchischer Mean gebildet:
       zuerst Mittelwert je Untergruppe, dann Mittelwert der Untergruppen.
    4. Die Dimensionen werden theoriegeleitet gewichtet.
    5. Ein Gate min(Frequenz, Aggression/Toxizität) verhindert hohe Scores
       bei nur hoher Aktivität ohne negative/aggressive Kommunikation.
    """

    def __init__(
        self,
        history_window_size: int = 5,
        min_history: int = 3,
        dimension_combiner: DimensionCombiner = "mean",
        dimensions: Optional[List[DimensionSpec]] = None,
        p_value_for_full_evidence: float = 0.01,
    ):
        self.dimensions = dimensions or DEFAULT_DIMENSIONS
        self._validate_weights(self.dimensions)

        self.history = ThreadMetricHistory(history_window_size=history_window_size)
        self.p_values = PValueCalculator(min_history=min_history)
        self.dimension_combiner = dimension_combiner
        self.p_value_combiner = PValueCombiner(method=dimension_combiner)
        self.evidence = EvidenceTransformer(p_value_for_full_evidence=p_value_for_full_evidence)
        self.warning_policy = WarningLevelPolicy()

    def calculate_final_score(self, thread_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        previous_barometer_values = self.history.previous_barometer_values(thread_id)

        dimension_results = self._analyze_dimensions(thread_id, metrics)
        score_raw = self._calculate_weighted_score(dimension_results)
        gate = self._calculate_gate(dimension_results)
        barometer_score = score_raw * gate
        barometer_percent = round(barometer_score * 100, 2)
        warning_level = self.warning_policy.decide(barometer_score, dimension_results)

        metrics_for_history = dict(metrics)
        metrics_for_history.update(
            {
                "barometer_score_0_1": round(barometer_score, 4),
                "shitstorm_barometer": barometer_percent,
                "warning_level": warning_level,
            }
        )
        self.history.append(thread_id, metrics_for_history)

        return {
            "thread_id": thread_id,
            "barometer_score_0_1": round(barometer_score, 4),
            "shitstorm_barometer": barometer_percent,
            "warning_level": warning_level,
            "score_raw_0_1": round(score_raw, 4),
            "gate_0_1": round(gate, 4),
            "dimension_scores": {
                name: round(result.evidence_score, 4)
                for name, result in dimension_results.items()
            },
            "dimension_weights": {
                dimension.name: dimension.weight
                for dimension in self.dimensions
            },
            "dimension_results": {
                name: result.as_dict()
                for name, result in dimension_results.items()
            },
            "recent_barometer_values": previous_barometer_values,
            "method": {
                "indicator_p_values": "poisson for count indicators, empirical upper-tail p-values for ratios/scores",
                "indicator_evidence_transform": "E_i = min(1, -log10(p_i) / 2), full evidence at p <= 0.01",
                "dimension_combination": self._method_description(),
                "aggregation": "Score_raw = weighted sum of dimension evidence scores; final score = Score_raw * min(Frequency, Aggression/Toxicity)",
            },
        }

    def _analyze_dimensions(self, thread_id: str, metrics: Dict[str, Any]) -> Dict[str, DimensionResult]:
        results: Dict[str, DimensionResult] = {}

        for dimension in self.dimensions:
            indicator_results = self._analyze_indicators(thread_id, metrics, dimension.indicators)
            p_dimension, evidence_score, subgroup_scores, combiner_name = self._combine_dimension(
                indicator_results
            )

            results[dimension.name] = DimensionResult(
                name=dimension.name,
                label=dimension.label,
                weight=dimension.weight,
                p_value=p_dimension,
                evidence_score=evidence_score,
                combiner=combiner_name,
                indicators=indicator_results,
                subgroup_scores=subgroup_scores,
            )

        return results

    def _analyze_indicators(
        self,
        thread_id: str,
        metrics: Dict[str, Any],
        indicators: List[IndicatorSpec],
    ) -> Dict[str, IndicatorResult]:
        results: Dict[str, IndicatorResult] = {}

        for indicator in indicators:
            current_value = SafeNumber.to_float(metrics.get(indicator.name, 0.0))
            previous_values = self.history.previous_metric_values(thread_id, indicator.name)
            p_value = self.p_values.calculate(indicator.method, current_value, previous_values)
            evidence_score = self.evidence.transform(p_value)

            results[indicator.name] = IndicatorResult(
                name=indicator.name,
                current_value=current_value,
                previous_values=previous_values,
                p_value=p_value,
                evidence_score=evidence_score,
                method=indicator.method,
                description=indicator.description,
                group=indicator.group,
            )

        return results

    def _combine_dimension(
        self,
        indicator_results: Dict[str, IndicatorResult],
    ) -> tuple[Optional[float], float, Dict[str, float], str]:
        if self.dimension_combiner == "mean":
            evidence_score, subgroup_scores = self._hierarchical_mean(indicator_results)
            return None, evidence_score, subgroup_scores, "hierarchical_mean"

        p_dimension = self.p_value_combiner.combine(
            result.p_value for result in indicator_results.values()
        )
        evidence_score = self.evidence.transform(p_dimension)
        subgroup_scores = self._subgroup_means_for_explanation(indicator_results)
        return p_dimension, evidence_score, subgroup_scores, self.dimension_combiner

    @staticmethod
    def _hierarchical_mean(indicator_results: Dict[str, IndicatorResult]) -> tuple[float, Dict[str, float]]:
        """Bildet zuerst Mittelwerte pro Untergruppe und dann den Mittelwert der Gruppen."""
        subgroup_values: Dict[str, List[float]] = defaultdict(list)

        for result in indicator_results.values():
            subgroup_values[result.group].append(result.evidence_score)

        subgroup_scores = {
            group: ShitstormScorer._mean(values)
            for group, values in subgroup_values.items()
        }

        dimension_score = ShitstormScorer._mean(list(subgroup_scores.values()))
        return dimension_score, subgroup_scores

    @staticmethod
    def _subgroup_means_for_explanation(indicator_results: Dict[str, IndicatorResult]) -> Dict[str, float]:
        subgroup_values: Dict[str, List[float]] = defaultdict(list)

        for result in indicator_results.values():
            subgroup_values[result.group].append(result.evidence_score)

        return {
            group: ShitstormScorer._mean(values)
            for group, values in subgroup_values.items()
        }

    @staticmethod
    def _mean(values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def _calculate_weighted_score(dimension_results: Dict[str, DimensionResult]) -> float:
        return sum(
            result.weight * result.evidence_score
            for result in dimension_results.values()
        )

    @staticmethod
    def _calculate_gate(dimension_results: Dict[str, DimensionResult]) -> float:
        frequency = dimension_results["frequency"].evidence_score
        aggression = dimension_results["aggression_toxicity"].evidence_score
        return min(frequency, aggression)

    def _method_description(self) -> str:
        if self.dimension_combiner == "mean":
            return "hierarchical mean of indicator evidence scores: mean within subgroups, then mean across subgroups"
        return f"{self.dimension_combiner} p-value combination per dimension, then p-value to evidence score"

    @staticmethod
    def _validate_weights(dimensions: List[DimensionSpec]) -> None:
        total_weight = sum(dimension.weight for dimension in dimensions)
        if not math.isclose(total_weight, 1.0, abs_tol=1e-9):
            raise ValueError(f"Dimension weights must sum to 1.0, got {total_weight}.")
