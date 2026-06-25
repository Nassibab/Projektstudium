"""Konfiguration der Dimensionen und Indikatoren.

Die Dimensionen bilden ein theoretisches Shitstorm-Konstrukt ab:
1. Frequenz 
2. Aggression / Toxizität / Negativität
3. Eskalationsdynamik
4. Fokus / Personalisierung

 Die ML-Rollenwahrscheinlichkeiten werden hier als weiche Zusatzsignale genutzt,
nicht als Ersatz für die LLM-/Regelmetriken. 
"""

from __future__ import annotations

from typing import List

from .models import DimensionSpec, IndicatorSpec

DEFAULT_DIMENSIONS: List[DimensionSpec] = [
    DimensionSpec(
        name="frequency",
        label="Frequenz / Mobilisierung",
        weight=0.25,
        indicators=[
            IndicatorSpec(
                "comment_count",
                "poisson",
                "Anzahl Kommentare im aktuellen 5-Minuten-Fenster",
                group="volume",
            ),
            IndicatorSpec(
                "unique_users",
                "empirical",
                "Anzahl unterschiedlicher Nutzer im aktuellen 5-Minuten-Fenster",
                group="participation",
            ),
            IndicatorSpec(
                "multi_user_ratio",
                "empirical",
                "Anteil nicht-dominanter Beteiligung; hoch bedeutet eher kollektive Mobilisierung als Einzelspam",
                group="participation",
            ),
        ],
    ),
    DimensionSpec(
        name="aggression_toxicity",
        label="Aggression / Toxizität / Negativität",
        weight=0.40,
        indicators=[
            IndicatorSpec("attack_count", "poisson", "Anzahl angreifender Kommentare", group="attack"),
            IndicatorSpec("attack_ratio", "empirical", "Anteil angreifender Kommentare", group="attack"),
            IndicatorSpec("attack_score_mean_norm", "empirical", "Normierter mittlerer Angriffsscore", group="attack"),
            IndicatorSpec("attack_probability_mean", "empirical", "Mittlere Rollenwahrscheinlichkeit für Attacke", group="attack_soft_role"),

            IndicatorSpec("toxic_count", "poisson", "Anzahl toxischer Kommentare, toxicity_score >= 3", group="toxicity"),
            IndicatorSpec("toxic_ratio", "empirical", "Anteil toxischer Kommentare", group="toxicity"),
            IndicatorSpec("toxicity_score_mean_norm", "empirical", "Normierter mittlerer Toxizitätsscore", group="toxicity"),

            IndicatorSpec("insult_comment_count", "poisson", "Anzahl Kommentare mit Beleidigungen", group="negative_language"),
            IndicatorSpec("insult_ratio", "empirical", "Anteil Kommentare mit Beleidigungen", group="negative_language"),
            IndicatorSpec("swearword_comment_count", "poisson", "Anzahl Kommentare mit Schimpfwörtern", group="negative_language"),
            IndicatorSpec("swearword_ratio", "empirical", "Anteil Kommentare mit Schimpfwörtern", group="negative_language"),
            IndicatorSpec("negative_word_count_mean", "empirical", "Mittlere Anzahl negativer Wörter", group="negative_language"),
        ],
    ),
    DimensionSpec(
        name="dynamics",
        label="Dynamik / Eskalationsverlauf",
        weight=0.20,
        indicators=[
            IndicatorSpec(
                "recent_attack_rate_3_mean",
                "empirical",
                "Kurzfristige Angriffsdichte über drei Kommentare",
                group="attack_rate",
            ),
            IndicatorSpec(
                "recent_attack_rate_5_mean",
                "empirical",
                "Kurzfristige Angriffsdichte über fünf Kommentare",
                group="attack_rate",
            ),
            IndicatorSpec(
                "attack_streak_max",
                "empirical",
                "Maximale Folge angreifender Kommentare",
                group="streak",
            ),
            IndicatorSpec(
                "reply_after_attack_ratio",
                "empirical",
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
            IndicatorSpec("direct_address_mean", "empirical", "Mittlere direkte Ansprachen", group="direct_address"),
            IndicatorSpec("accusation_marker_mean", "empirical", "Mittlere Anzahl von Beschuldigungsmarkern", group="conflict_markers"),
            IndicatorSpec("mockery_marker_mean", "empirical", "Mittlere Anzahl von Spott-/Abwertungsmarkern", group="conflict_markers"),
            IndicatorSpec("target_recently_attacked_ratio", "empirical", "Anteil Kommentare mit kürzlich angegriffenem Ziel", group="target_focus"),
        ],
    ),
]
