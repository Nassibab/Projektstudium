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
    WarningLevel,
)
from .policy import WarningLevelPolicy
from .statistics_tools import EvidenceTransformer, PValueCalculator, PValueCombiner


class ShitstormScorer:
    """Berechnet ein Shitstorm-Barometer als Composite Indicator.

    1. Fensterwerte werden relativ zur bisherigen Thread-Historie geprüft.
    2. Zusätzlich gibt es absolute Evidenzscores, damit frühe Eskalationen nicht
       fälschlich auf 0 bleiben, nur weil noch keine drei Vergleichsfenster existieren.
    3. Pro Dimension wird max(relative Evidenz, absolute Evidenz) verwendet.
    4. Final gilt: Shitstorm braucht Frequenz UND Aggression. Darum wird der
       gewichtete Dimensionsscore mit einem weichen Core-Gate sqrt(Frequenz * Aggression)
       multipliziert.
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
        current_window_start = metrics.get("window_start")
        previous_barometer_values = self.history.previous_barometer_values(
            thread_id,
            current_window_start=current_window_start,
        )

        relative_dimension_results = self._analyze_dimensions(thread_id, metrics)
        absolute_dimension_scores = self._absolute_dimension_scores(metrics)
        dimension_results = self._merge_relative_and_absolute(
            relative_dimension_results,
            absolute_dimension_scores,
        )

        score_raw = self._calculate_weighted_score(dimension_results)
        gate = self._calculate_gate(dimension_results)
        barometer_score = min(1.0, score_raw * gate)
        barometer_percent = round(barometer_score * 100, 2)
        warning_level = self.warning_policy.decide(barometer_score, dimension_results)

        absolute_critical = self._absolute_critical_override(metrics)
        if absolute_critical:
            barometer_score = max(barometer_score, 0.60)
            barometer_percent = round(barometer_score * 100, 2)
            warning_level = WarningLevel.CRITICAL.value

        metrics_for_history = dict(metrics)
        metrics_for_history.update(
            {
                "barometer_score_0_1": round(barometer_score, 4),
                "shitstorm_barometer": barometer_percent,
                "warning_level": warning_level,
            }
        )
        self.history.upsert(thread_id, metrics_for_history)

        return {
            "thread_id": thread_id,
            "barometer_score_0_1": round(barometer_score, 4),
            "shitstorm_barometer": barometer_percent,
            "warning_level": warning_level,
            "score_raw_0_1": round(score_raw, 4),
            "gate_0_1": round(gate, 4),
            "absolute_critical_override": absolute_critical,
            "dimension_scores": {
                name: round(result.evidence_score, 4)
                for name, result in dimension_results.items()
            },
            "dimension_scores_relative": {
                name: round(result.evidence_score, 4)
                for name, result in relative_dimension_results.items()
            },
            "dimension_scores_absolute": {
                name: round(value, 4)
                for name, value in absolute_dimension_scores.items()
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
                "indicator_evidence_transform": "relative E_i = min(1, -log10(p_i) / 2), full relative evidence at p <= 0.01",
                "absolute_evidence": "predefined saturation functions per theoretical dimension; calibrate thresholds on labeled validation data",
                "dimension_combination": self._method_description(),
                "aggregation": "Dimension score = max(relative evidence, absolute evidence); Score_raw = weighted sum; final = Score_raw * sqrt(Frequency * Aggression/Toxicity)",
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
        current_window_start = metrics.get("window_start")

        for indicator in indicators:
            current_value = SafeNumber.to_float(metrics.get(indicator.name, 0.0))
            previous_values = self.history.previous_metric_values(
                thread_id,
                indicator.name,
                current_window_start=current_window_start,
            )
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
    def _clip01(value: float) -> float:
        return min(1.0, max(0.0, float(value)))

    @classmethod
    def _sat(cls, value: Any, low: float, high: float) -> float:
        value = SafeNumber.to_float(value)
        if high <= low:
            return 0.0
        return cls._clip01((value - low) / (high - low))

    @classmethod
    def _absolute_dimension_scores(cls, metrics: Dict[str, Any]) -> Dict[str, float]:
        """Absolute Evidenzscores für frühe Fenster und robuste Mindestinterpretation.

        Die Schwellen sind fachliche Startwerte. Für wissenschaftliche Auswertung: 
        auf gelabelten Threads per ROC/PR-Kurve oder ordinaler Kalibrierung...
        """
        frequency = cls._mean([
            cls._sat(metrics.get("comment_count"), 3, 15),
            cls._sat(metrics.get("unique_users"), 2, 8),
            cls._clip01(SafeNumber.to_float(metrics.get("multi_user_ratio"))),
        ])

        aggression_toxicity = cls._mean([
            cls._clip01(SafeNumber.to_float(metrics.get("attack_ratio"))),
            cls._clip01(SafeNumber.to_float(metrics.get("toxic_ratio"))),
            cls._clip01(SafeNumber.to_float(metrics.get("attack_score_mean_norm"))),
            cls._clip01(SafeNumber.to_float(metrics.get("toxicity_score_mean_norm"))),
            cls._sat(metrics.get("negative_word_count_mean"), 0.5, 3.0),
            cls._clip01(SafeNumber.to_float(metrics.get("insult_ratio"))),
            cls._clip01(SafeNumber.to_float(metrics.get("swearword_ratio"))),
            # Weiches ML-Rollensignal, bewusst niedrig indirekt gewichtet durch Mittelwert.
            cls._clip01(SafeNumber.to_float(metrics.get("attack_probability_mean"))),
        ])

        dynamics = cls._mean([
            cls._clip01(SafeNumber.to_float(metrics.get("recent_attack_rate_3_mean"))),
            cls._clip01(SafeNumber.to_float(metrics.get("recent_attack_rate_5_mean"))),
            cls._sat(metrics.get("attack_streak_max"), 1, 5),
            cls._clip01(SafeNumber.to_float(metrics.get("reply_after_attack_ratio"))),
        ])

        focus_personalization = cls._mean([
            cls._sat(metrics.get("direct_address_mean"), 0.0, 2.0),
            cls._sat(metrics.get("accusation_marker_mean"), 0.0, 1.5),
            cls._sat(metrics.get("mockery_marker_mean"), 0.0, 1.5),
            cls._clip01(SafeNumber.to_float(metrics.get("target_recently_attacked_ratio"))),
        ])

        return {
            "frequency": frequency,
            "aggression_toxicity": aggression_toxicity,
            "dynamics": dynamics,
            "focus_personalization": focus_personalization,
        }

    @staticmethod
    def _merge_relative_and_absolute(
        relative_results: Dict[str, DimensionResult],
        absolute_scores: Dict[str, float],
    ) -> Dict[str, DimensionResult]:
        merged: Dict[str, DimensionResult] = {}

        for name, result in relative_results.items():
            absolute_score = absolute_scores.get(name, 0.0)
            evidence_score = max(result.evidence_score, absolute_score)

            merged[name] = DimensionResult(
                name=result.name,
                label=result.label,
                weight=result.weight,
                p_value=result.p_value,
                evidence_score=evidence_score,
                combiner=f"{result.combiner}+absolute_max",
                indicators=result.indicators,
                subgroup_scores={
                    **result.subgroup_scores,
                    "relative_model": result.evidence_score,
                    "absolute_rule": absolute_score,
                },
            )

        return merged

    @staticmethod
    def _calculate_weighted_score(dimension_results: Dict[str, DimensionResult]) -> float:
        return sum(
            result.weight * result.evidence_score
            for result in dimension_results.values()
        )

    @staticmethod
    def _calculate_gate(dimension_results: Dict[str, DimensionResult]) -> float:
        frequency = max(0.0, dimension_results["frequency"].evidence_score)
        aggression = max(0.0, dimension_results["aggression_toxicity"].evidence_score)
        return math.sqrt(frequency * aggression)

    @staticmethod
    def _absolute_critical_override(metrics: Dict[str, Any]) -> bool:
        return (
            SafeNumber.to_float(metrics.get("comment_count")) >= 10
            and SafeNumber.to_float(metrics.get("unique_users")) >= 4
            and SafeNumber.to_float(metrics.get("attack_ratio")) >= 0.70
            and SafeNumber.to_float(metrics.get("toxic_ratio")) >= 0.60
            and SafeNumber.to_float(metrics.get("attack_streak_max")) >= 5
        )

    def _method_description(self) -> str:
        if self.dimension_combiner == "mean":
            return "hierarchical mean of indicator evidence scores: mean within subgroups, then mean across subgroups"
        return f"{self.dimension_combiner} p-value combination per dimension, then p-value to evidence score"

    @staticmethod
    def _validate_weights(dimensions: List[DimensionSpec]) -> None:
        total_weight = sum(dimension.weight for dimension in dimensions)
        if not math.isclose(total_weight, 1.0, abs_tol=1e-9):
            raise ValueError(f"Dimension weights must sum to 1.0, got {total_weight}.")
