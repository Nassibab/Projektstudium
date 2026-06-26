"""Datenmodelle für das Shitstorm-Barometer.

Dieses Modul enthält nur Typen und kleine Hilfsklassen.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

# alle relativen Indikatoren werden als positiver
# Rolling-z-Score plus einseitiges CUSUM bewertet.
IndicatorMethod = Literal["rolling_z_cusum"]

# Rückwärtskompatibler Alias, falls andere Module den alten Namen importieren.
PValueMethod = IndicatorMethod

# Der produktive Scorer nutzt weiterhin den hierarchischen Mittelwert.
DimensionCombiner = Literal["mean"]


class WarningLevel(str, Enum):
    NORMAL = "normal"
    WATCH = "watch"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class IndicatorSpec:
    """Beschreibt, wie ein einzelner Indikator bewertet wird.

    group wird für den hierarchischen Mean verwendet:
    Erst werden Indikatoren innerhalb einer group gemittelt, danach die Gruppen.
    Dadurch bekommt eine Untergruppe nicht nur deshalb mehr Gewicht, weil sie
    mehr Einzelvariablen enthält.
    """

    name: str
    method: IndicatorMethod = "rolling_z_cusum"
    description: str = ""
    group: str = "default"


@dataclass(frozen=True)
class DimensionSpec:
    """Bündelt mehrere Indikatoren zu einer fachlichen Eskalationsdimension."""

    name: str
    label: str
    weight: float
    indicators: List[IndicatorSpec]


@dataclass(frozen=True)
class IndicatorResult:
    """Ergebnis für einen einzelnen Indikator im aktuellen Fenster.

    """

    name: str
    current_value: float
    previous_values: List[float]
    evidence_score: float
    method: str
    description: str
    group: str = "default"

    rolling_mean: Optional[float] = None
    rolling_std: Optional[float] = None
    z_score: Optional[float] = None
    z_evidence_score: Optional[float] = None
    cusum_value: Optional[float] = None
    cusum_evidence_score: Optional[float] = None
    has_sufficient_history: bool = True
    insufficient_history_message: Optional[str] = None
    p_value: Optional[float] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "current_value": round(self.current_value, 4),
            "previous_values": [round(value, 4) for value in self.previous_values],
            "p_value": None if self.p_value is None else round(self.p_value, 6),
            "evidence_score": round(self.evidence_score, 4),
            "method": self.method,
            "group": self.group,
            "description": self.description,
            "rolling_mean": None if self.rolling_mean is None else round(self.rolling_mean, 4),
            "rolling_std": None if self.rolling_std is None else round(self.rolling_std, 4),
            "z_score": None if self.z_score is None else round(self.z_score, 4),
            "z_evidence_score": None if self.z_evidence_score is None else round(self.z_evidence_score, 4),
            "cusum_value": None if self.cusum_value is None else round(self.cusum_value, 4),
            "cusum_evidence_score": None if self.cusum_evidence_score is None else round(self.cusum_evidence_score, 4),
            "has_sufficient_history": self.has_sufficient_history,
            "insufficient_history_message": self.insufficient_history_message,
        }


@dataclass(frozen=True)
class DimensionResult:
    """Ergebnis für eine Dimension wie Frequenz, Aggression oder Dynamik."""

    name: str
    label: str
    weight: float
    p_value: Optional[float]
    evidence_score: float
    combiner: str
    indicators: Dict[str, IndicatorResult]
    subgroup_scores: Dict[str, float]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "weight": self.weight,
            "p_value": None if self.p_value is None else round(self.p_value, 6),
            "evidence_score": round(self.evidence_score, 4),
            "combiner": self.combiner,
            "subgroup_scores": {
                name: round(score, 4)
                for name, score in self.subgroup_scores.items()
            },
            "indicator_results": {
                name: result.as_dict()
                for name, result in self.indicators.items()
            },
        }


class SafeNumber:
    """Konvertierung beliebiger Metrikwerte in float."""

    @staticmethod
    def to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default
