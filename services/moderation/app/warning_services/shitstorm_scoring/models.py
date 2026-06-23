"""Datenmodelle für das Shitstorm-Barometer.

Dieses Modul enthält nur Typen und kleine Hilfsklassen.
Keine Berechnungslogik, damit der Code übersichtlich bleibt.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

PValueMethod = Literal["poisson", "empirical"]
DimensionCombiner = Literal["mean", "bonferroni", "fisher"]


class WarningLevel(str, Enum):
    NORMAL = "normal"
    WATCH = "watch"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class IndicatorSpec:
    """Beschreibt, wie ein einzelner Indikator geprüft wird.

    group wird für den hierarchischen Mean verwendet:
    Erst werden Indikatoren innerhalb einer group gemittelt, danach die Gruppen.
    Dadurch bekommt eine Untergruppe nicht nur deshalb mehr Gewicht, weil sie
    mehr Einzelvariablen enthält.
    """

    name: str
    method: PValueMethod
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
    """Ergebnis für einen einzelnen Indikator im aktuellen Fenster."""

    name: str
    current_value: float
    previous_values: List[float]
    p_value: float
    evidence_score: float
    method: str
    description: str
    group: str = "default"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "current_value": round(self.current_value, 4),
            "previous_values": [round(value, 4) for value in self.previous_values],
            "p_value": round(self.p_value, 6),
            "evidence_score": round(self.evidence_score, 4),
            "method": self.method,
            "group": self.group,
            "description": self.description,
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
    """ Konvertierung beliebiger Metrikwerte in float."""

    @staticmethod
    def to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default
