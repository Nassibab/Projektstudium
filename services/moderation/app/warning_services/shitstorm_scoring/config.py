"""Konfiguration der Dimensionen und Indikatoren.

Die Dimensionen bilden ein theoretisches Shitstorm-Konstrukt ab:
1. Frequenz
2. Aggression / Toxizität / Negativität
3. Eskalationsdynamik
4. Fokus / Personalisierung

Alle relativen Indikatoren werden über Rolling-z-Score plus einseitiges CUSUM
bewertet.

Gewichte nach aktueller Barometer-Konstruktion:
- Frequenz / Aktivität: 0.25
- Aggression / Toxizität / Negativität: 0.35
- Dynamik / Eskalationsverlauf: 0.25
- Fokus / Personalisierung: 0.15
"""

from __future__ import annotations

from typing import List

from .models import DimensionSpec, IndicatorSpec

METHOD = "rolling_z_cusum"

DEFAULT_DIMENSIONS: List[DimensionSpec] = [
    DimensionSpec(
        name="frequency",
        label="Frequenz / Mobilisierung",
        weight=0.25,
        indicators=[
            IndicatorSpec(
                "comment_count",
                METHOD,
                "Anzahl Kommentare im aktuellen Zeitfenster",
                group="volume",
            ),
            IndicatorSpec(
                "unique_users",
                METHOD,
                "Anzahl unterschiedlicher Nutzer im aktuellen Zeitfenster",
                group="participation",
            ),
            IndicatorSpec(
                "multi_user_ratio",
                METHOD,
                "Anteil nicht-dominanter Beteiligung; hoch bedeutet eher kollektive Mobilisierung als Einzelspam",
                group="participation",
            ),
        ],
    ),
    DimensionSpec(
        name="aggression_toxicity",
        label="Aggression / Toxizität / Negativität",
        weight=0.35,
        indicators=[
            IndicatorSpec("attack_count", METHOD, "Anzahl angreifender Kommentare", group="attack"),
            IndicatorSpec("attack_ratio", METHOD, "Anteil angreifender Kommentare", group="attack"),
            IndicatorSpec("attack_score_mean_norm", METHOD, "Normierter mittlerer Angriffsscore", group="attack"),
            IndicatorSpec("attack_probability_mean", METHOD, "Mittlere Rollenwahrscheinlichkeit für Attacke", group="attack_soft_role"),

            IndicatorSpec("toxic_count", METHOD, "Anzahl toxischer Kommentare, toxicity_score >= 3", group="toxicity"),
            IndicatorSpec("toxic_ratio", METHOD, "Anteil toxischer Kommentare", group="toxicity"),
            IndicatorSpec("toxicity_score_mean_norm", METHOD, "Normierter mittlerer Toxizitätsscore", group="toxicity"),

            IndicatorSpec("insult_comment_count", METHOD, "Anzahl Kommentare mit Beleidigungen", group="negative_language"),
            IndicatorSpec("insult_ratio", METHOD, "Anteil Kommentare mit Beleidigungen", group="negative_language"),
            IndicatorSpec("swearword_comment_count", METHOD, "Anzahl Kommentare mit Schimpfwörtern", group="negative_language"),
            IndicatorSpec("swearword_ratio", METHOD, "Anteil Kommentare mit Schimpfwörtern", group="negative_language"),
            IndicatorSpec("negative_word_count_mean", METHOD, "Mittlere Anzahl negativer Wörter", group="negative_language"),
        ],
    ),
    DimensionSpec(
        name="dynamics",
        label="Dynamik / Eskalationsverlauf",
        weight=0.25,
        indicators=[
            IndicatorSpec(
                "recent_attack_rate_3_mean",
                METHOD,
                "Kurzfristige Angriffsdichte über drei Kommentare",
                group="attack_rate",
            ),
            IndicatorSpec(
                "recent_attack_rate_5_mean",
                METHOD,
                "Kurzfristige Angriffsdichte über fünf Kommentare",
                group="attack_rate",
            ),
            IndicatorSpec(
                "attack_streak_max",
                METHOD,
                "Maximale Folge angreifender Kommentare",
                group="streak",
            ),
            IndicatorSpec(
                "reply_after_attack_ratio",
                METHOD,
                "Anteil Antworten nach einem Angriff",
                group="interaction_after_attack",
            ),
        ],
    ),
    DimensionSpec(
        name="focus_personalization",
        label="Fokus / Personalisierung",
        weight=0.15,
        indicators=[
            IndicatorSpec("direct_address_mean", METHOD, "Mittlere direkte Ansprachen", group="direct_address"),
            IndicatorSpec("accusation_marker_mean", METHOD, "Mittlere Anzahl von Beschuldigungsmarkern", group="conflict_markers"),
            IndicatorSpec("mockery_marker_mean", METHOD, "Mittlere Anzahl von Spott-/Abwertungsmarkern", group="conflict_markers"),
            IndicatorSpec("target_recently_attacked_ratio", METHOD, "Anteil Kommentare mit kürzlich angegriffenem Ziel", group="target_focus"),
        ],
    ),
]
