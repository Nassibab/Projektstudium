# app/evaluation_window_json_report.py

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


WINDOW_REPORT_FIELDS = [
    "thread_id",
    "window_start",
    "window_end",
    "comment_count",
    "unique_users",
    "dominant_user_ratio",
    "multi_user_ratio",
    "thread_user_count",
    "thread_comment_count",
    "thread_mean_comments_per_user",
    "thread_max_comments_by_one_user",
    "thread_single_comment_user_count",
    "thread_max_user_share",
    "thread_single_comment_user_share",
    "attack_count",
    "attack_ratio",
    "attack_score_mean",
    "attack_score_mean_norm",
    "attack_score_max",
    "attack_probability_mean",
    "toxic_count",
    "toxic_ratio",
    "toxicity_score_mean",
    "toxicity_score_mean_norm",
    "toxicity_score_max",
    "insult_comment_count",
    "insult_ratio",
    "insult_count_sum",
    "swearword_comment_count",
    "swearword_ratio",
    "negative_word_count_mean",
    "recent_attack_rate_3_mean",
    "recent_attack_rate_5_mean",
    "attack_streak_max",
    "reply_after_attack_ratio",
    "direct_address_mean",
    "imperative_mean",
    "accusation_marker_mean",
    "mockery_marker_mean",
    "target_recently_attacked_ratio",
    "counter_speech_probability_mean",
    "target_response_probability_mean",
    "deescalation_probability_mean",
    "irony_mean",
    "reply_depth_mean",
    "reply_depth_max",
    "num_children_mean",
]


def collect_aggregated_windows(service) -> list[dict[str, Any]]:
    """
    Sammelt alle final aggregierten Fenster aus dem WindowStore.

    Die Felder entsprechen dem neuen Standardvariablen-Aggregator. Alte
    Analyse-R-Zwischenfelder werden hier nicht mehr erwartet.
    """

    rows: list[dict[str, Any]] = []

    for (thread_id, window_start), _comments in service.store.windows.items():
        metrics = service.aggregator.aggregate(thread_id, window_start)
        row = {field: metrics.get(field) for field in WINDOW_REPORT_FIELDS}
        rows.append(row)

    rows.sort(key=lambda row: (str(row["thread_id"]), str(row["window_start"])))
    return rows


def print_aggregated_windows_log(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print("\nKeine aggregierten Fenster vorhanden.")
        return

    print("\n" + "=" * 140)
    print("AGGREGIERTE FENSTER - NEUES STANDARDFORMAT")
    print("=" * 140)

    for row in rows:
        print(
            "window={window_start} | comments={comment_count} | users={unique_users} | "
            "dominant_user={dominant_user_ratio} | attacks={attack_count} | "
            "attack_ratio={attack_ratio} | toxic_ratio={toxic_ratio} | "
            "attack_mean={attack_score_mean} | attack_prob={attack_probability_mean} | "
            "tox_mean={toxicity_score_mean} | streak={attack_streak_max}".format(**row)
        )


def save_window_report_json(
    service,
    output_dir: Path | str,
    run_name: str,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = collect_aggregated_windows(service)

    print_aggregated_windows_log(rows)

    output_path = output_dir / f"{run_name}_windows.json"

    payload = {
        "run_name": run_name,
        "input_format": "new_standard_variables_direct",
        "window_count": len(rows),
        "windows": rows,
    }

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)

    print(f"\nWindow-Ausgabe gespeichert unter: {output_path}")

    return {
        "path": str(output_path),
        "window_count": len(rows),
        "windows": rows,
    }
