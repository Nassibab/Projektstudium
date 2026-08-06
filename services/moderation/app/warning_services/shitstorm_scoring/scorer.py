"""Hauptlogik für das Shitstorm-Barometer.

Aktuelle Variante:
- keine frei gesetzten absoluten Ersatzwerte,
- relative Bewertung ausschließlich über Rolling-z-Score und positives CUSUM,
- bei zu wenig Historie wird das Ergebnis als vorläufig markiert,
- Barometer-Konstruktion als gewichteter Composite Indicator,
- finaler Score wird durch Aggression/Toxizität/Negativität nach oben begrenzt.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

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
from .statistics_tools import RollingZCusumDetector


class ShitstormScorer:
    """Berechnet ein Shitstorm-Barometer als relativen Composite Indicator.

    Ablauf:
    1. Jede Fenstermetrik wird relativ zur bisherigen Thread-Historie bewertet.
    2. Rolling-z erkennt abrupte Peaks.
    3. Ein einseitiges positives CUSUM erkennt kumulative Eskalationen.
    4. Pro Indikator gilt: Evidenz = max(z-Evidenz, CUSUM-Evidenz).
    5. Pro Dimension werden Indikatoren erst innerhalb fachlicher Untergruppen
       und anschließend über Untergruppen gemittelt.
    6. Score_raw ist die gewichtete Summe der vier Dimensionsscores:
       0.25*F + 0.35*A + 0.25*D + 0.15*P.
    7. Score_final = min(Score_raw, Aggression/Toxizität/Negativität).
       Dadurch kann der Barometerwert ohne aggressiv-toxischen Kern nicht hoch werden.
    8. Die Warnstufe wird anschließend über kalibrierbare Schwellen des finalen
       Barometerwerts abgeleitet.

    Wenn weniger als min_history frühere Fenster vorhanden sind, wird bewusst
    kein absoluter Fallback verwendet. Der Score bleibt 0 und der Status erklärt,
    dass noch nicht genug Vergleichsdaten vorliegen.
    """

    def __init__(
        self,
        history_window_size: int = 5,
        min_history: int = 3,
        dimension_combiner: DimensionCombiner = "mean",
        dimensions: Optional[List[DimensionSpec]] = None,
        z_watch: float = 1.0,
        z_full: float = 3.0,
        cusum_reference: float = 0.5,
        cusum_watch: float = 1.5,
        cusum_full: float = 5.0,
        watch_threshold: float = 0.20,
        warning_threshold: float = 0.40,
        critical_threshold: float = 0.60,
    ):
        if dimension_combiner != "mean":
            raise ValueError(
                "Nach der Umstellung auf Rolling-z/CUSUM wird nur "
                "dimension_combiner='mean' unterstützt. Bonferroni/Fisher "
                "gehören zur alten p-Wert-Logik."
            )

        self.dimensions = dimensions or DEFAULT_DIMENSIONS
        self._validate_weights(self.dimensions)

        self.history = ThreadMetricHistory(history_window_size=history_window_size)
        self.detector = RollingZCusumDetector(
            min_history=min_history,
            z_watch=z_watch,
            z_full=z_full,
            cusum_reference=cusum_reference,
            cusum_watch=cusum_watch,
            cusum_full=cusum_full,
        )
        self.dimension_combiner = dimension_combiner
        self.warning_policy = WarningLevelPolicy(
            watch_threshold=watch_threshold,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
        )

        # CUSUM muss fensterweise gespeichert werden. Bei Live-Auswertung wird
        # dasselbe Zeitfenster nach jedem neuen Kommentar neu aggregiert; es
        # darf daher nicht mehrfach als unabhängiger CUSUM-Schritt zählen.
        self._cusum_history: Dict[Tuple[Any, str], List[Dict[str, Any]]] = defaultdict(list)
        self._cusum_history_size = history_window_size + 1

    def calculate_final_score(self, thread_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        current_window_start = metrics.get("window_start")
        previous_barometer_values = self.history.previous_barometer_values(
            thread_id,
            current_window_start=current_window_start,
        )

        dimension_results = self._analyze_dimensions(thread_id, metrics)
        has_sufficient_history = self._has_sufficient_history(dimension_results)
        aggression_cap = self._aggression_score(dimension_results)

        if has_sufficient_history:
            score_raw = self._calculate_weighted_score(dimension_results)
            barometer_score = self._calculate_aggression_capped_score(score_raw, aggression_cap)
            cap_applied = barometer_score < score_raw
            policy_decision = self.warning_policy.evaluate(barometer_score, dimension_results)
            warning_level = policy_decision["warning_level"]
            evaluation_status = "ready"
            evaluation_message = "Rolling-z/CUSUM wurde auf Basis ausreichender Vergleichsfenster berechnet."
        else:
            score_raw = 0.0
            barometer_score = 0.0
            cap_applied = False
            warning_level = WarningLevel.NORMAL.value
            evaluation_status = "insufficient_history"
            evaluation_message = (
                "Noch nicht genug vorherige Vergleichsfenster für eine stabile "
                "relative Rolling-z/CUSUM-Bewertung. Es wird kein absoluter "
                "Ersatzscore verwendet."
            )
            policy_decision = self.warning_policy.evaluate(0.0, dimension_results)
            policy_decision.update(
                {
                    "warning_level": warning_level,
                    "reason": "insufficient_history_no_absolute_fallback",
                    "barometer_score": 0.0,
                }
            )

        barometer_percent = round(barometer_score * 100, 2)

        metrics_for_history = dict(metrics)
        metrics_for_history.update(
            {
                "barometer_score_0_1": round(barometer_score, 4),
                "shitstorm_barometer": barometer_percent,
                "warning_level": warning_level,
                "evaluation_status": evaluation_status,
            }
        )
        self.history.upsert(thread_id, metrics_for_history)

        return {
            "thread_id": thread_id,
            "barometer_score_0_1": round(barometer_score, 4),
            "shitstorm_barometer": barometer_percent,
            "warning_level": warning_level,
            "evaluation_status": evaluation_status,
            "evaluation_message": evaluation_message,
            "has_sufficient_history": has_sufficient_history,
            "score_raw_0_1": round(score_raw, 4),
            "score_final_0_1": round(barometer_score, 4),
            "aggression_cap_0_1": round(aggression_cap, 4),
            "cap_applied": cap_applied,
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
            "warning_decision": policy_decision,
            "recent_barometer_values": previous_barometer_values,
            "method": {
                "indicator_method": "positive rolling-z-score plus one-sided CUSUM",
                "indicator_evidence": "E_i = max(E_z, E_CUSUM), both scaled to 0..1",
                "insufficient_history_handling": (
                    "No absolute fallback. Until min_history previous windows exist, "
                    "score remains 0 and evaluation_status='insufficient_history'."
                ),
                "dimension_combination": self._method_description(),
                "aggregation": (
                    "Score_raw = 0.25*F + 0.35*A + 0.25*D + 0.15*P; "
                    "Score_final = min(Score_raw, Aggression/Toxicity); "
                    "Barometer = Score_final * 100."
                ),
                "warning_logic": (
                    "Threshold-only warning levels on the final aggression-capped "
                    "barometer score: normal < watch < warning < critical."
                ),
            },
        }

    def _analyze_dimensions(self, thread_id: str, metrics: Dict[str, Any]) -> Dict[str, DimensionResult]:
        results: Dict[str, DimensionResult] = {}

        for dimension in self.dimensions:
            indicator_results = self._analyze_indicators(thread_id, metrics, dimension.indicators)
            evidence_score, subgroup_scores = self._hierarchical_mean(indicator_results)

            results[dimension.name] = DimensionResult(
                name=dimension.name,
                label=dimension.label,
                weight=dimension.weight,
                p_value=None,
                evidence_score=evidence_score,
                combiner="hierarchical_mean_rolling_z_cusum_relative_only",
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
            previous_cusum = self._previous_cusum_value(
                thread_id=thread_id,
                indicator_name=indicator.name,
                current_window_start=current_window_start,
            )

            signal = self.detector.calculate(
                current_value=current_value,
                previous_values=previous_values,
                previous_cusum=previous_cusum,
            )
            self._upsert_cusum_value(
                thread_id=thread_id,
                indicator_name=indicator.name,
                window_start=current_window_start,
                cusum_value=signal.cusum_value,
            )

            results[indicator.name] = IndicatorResult(
                name=indicator.name,
                current_value=current_value,
                previous_values=previous_values,
                p_value=None,
                evidence_score=signal.evidence_score,
                method=signal.method,
                description=indicator.description,
                group=indicator.group,
                rolling_mean=signal.rolling_mean,
                rolling_std=signal.rolling_std,
                z_score=signal.z_score,
                z_evidence_score=signal.z_evidence_score,
                cusum_value=signal.cusum_value,
                cusum_evidence_score=signal.cusum_evidence_score,
                has_sufficient_history=signal.has_sufficient_history,
                insufficient_history_message=signal.insufficient_history_message,
            )

        return results

    def _previous_cusum_value(self, thread_id: Any, indicator_name: str, current_window_start: Any) -> float:
        key = (thread_id, indicator_name)
        history = [
            row for row in self._cusum_history[key]
            if not self._same_window(row.get("window_start"), current_window_start)
        ]
        if not history:
            return 0.0
        return SafeNumber.to_float(history[-1].get("cusum_value"), 0.0)

    def _upsert_cusum_value(
        self,
        thread_id: Any,
        indicator_name: str,
        window_start: Any,
        cusum_value: float,
    ) -> None:
        key = (thread_id, indicator_name)
        history = [
            row for row in self._cusum_history[key]
            if not self._same_window(row.get("window_start"), window_start)
        ]
        history.append({"window_start": window_start, "cusum_value": float(cusum_value)})
        self._cusum_history[key] = history[-self._cusum_history_size:]

    @staticmethod
    def _same_window(left: Any, right: Any) -> bool:
        return str(left) == str(right)

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
    def _has_sufficient_history(dimension_results: Dict[str, DimensionResult]) -> bool:
        indicator_results = [
            indicator
            for dimension in dimension_results.values()
            for indicator in dimension.indicators.values()
        ]
        return bool(indicator_results) and all(
            indicator.has_sufficient_history
            for indicator in indicator_results
        )

    @staticmethod
    def _mean(values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def _calculate_weighted_score(dimension_results: Dict[str, DimensionResult]) -> float:
        return min(1.0, max(0.0, sum(
            result.weight * result.evidence_score
            for result in dimension_results.values()
        )))

    @staticmethod
    def _aggression_score(dimension_results: Dict[str, DimensionResult]) -> float:
        return min(1.0, max(0.0, dimension_results["aggression_toxicity"].evidence_score))

    @staticmethod
    def _calculate_aggression_capped_score(score_raw: float, aggression_score: float) -> float:
        return min(1.0, max(0.0, min(float(score_raw), float(aggression_score))))

    def _method_description(self) -> str:
        return (
            "hierarchical mean of relative indicator evidence scores: "
            "mean within groups, then mean across groups"
        )

    @staticmethod
    def _validate_weights(dimensions: List[DimensionSpec]) -> None:
        total_weight = sum(dimension.weight for dimension in dimensions)
        if not math.isclose(total_weight, 1.0, abs_tol=1e-9):
            raise ValueError(f"Dimension weights must sum to 1.0, got {total_weight}.")
