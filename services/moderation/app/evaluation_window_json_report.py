# app/evaluation_window_json_report.py

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def collect_aggregated_windows(service) -> list[dict[str, Any]]:
    """
    Sammelt alle final aggregierten Fenster aus dem WindowStore.
    Pro 5-Minuten-Fenster wird genau einmal nach Verarbeitung aller Kommentare aggregiert.
    """

    rows: list[dict[str, Any]] = []

    for (thread_id, window_start), comments in service.store.windows.items():
        metrics = service.aggregator.aggregate(thread_id, window_start)

        row = {
            "thread_id": thread_id,
            "window_start": metrics.get("window_start"),
            "window_end": metrics.get("window_end"),

            "comment_count": metrics.get("comment_count"),
            "unique_users": metrics.get("unique_users"),
            "dominant_user_ratio": metrics.get("dominant_user_ratio"),

            "thread_user_count": metrics.get("thread_user_count"),
            "thread_comment_count": metrics.get("thread_comment_count"),
            "thread_max_user_share": metrics.get("thread_max_user_share"),

            "attack_count": metrics.get("attack_count"),
            "attack_ratio": metrics.get("attack_ratio"),
            "attack_score_mean": metrics.get("attack_score_mean"),
            "attack_score_max": metrics.get("attack_score_max"),

            "toxic_count": metrics.get("toxic_count"),
            "toxic_ratio": metrics.get("toxic_ratio"),
            "toxicity_score_mean": metrics.get("toxicity_score_mean"),
            "toxicity_score_max": metrics.get("toxicity_score_max"),

            "insult_comment_count": metrics.get("insult_comment_count"),
            "insult_ratio": metrics.get("insult_ratio"),
            "insult_count_sum": metrics.get("insult_count_sum"),
            "swearword_comment_count": metrics.get("swearword_comment_count"),
            "swearword_ratio": metrics.get("swearword_ratio"),
            "negative_word_count_mean": metrics.get("negative_word_count_mean"),

            "recent_attack_rate_3_mean": metrics.get("recent_attack_rate_3_mean"),
            "recent_attack_rate_5_mean": metrics.get("recent_attack_rate_5_mean"),
            "attack_streak_max": metrics.get("attack_streak_max"),
            "reply_after_attack_ratio": metrics.get("reply_after_attack_ratio"),

            "direct_address_mean": metrics.get("direct_address_mean"),
            "accusation_marker_mean": metrics.get("accusation_marker_mean"),
            "mockery_marker_mean": metrics.get("mockery_marker_mean"),
            "target_recently_attacked_ratio": metrics.get("target_recently_attacked_ratio"),
        }

        rows.append(row)

    rows.sort(key=lambda row: (str(row["thread_id"]), str(row["window_start"])))
    return rows


def print_aggregated_windows_log(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print("\nKeine aggregierten Fenster vorhanden.")
        return

    print("\n" + "=" * 120)
    print("AGGREGIERTE FENSTER")
    print("=" * 120)

    for row in rows:
        print(
            "window={window_start} | comments={comment_count} | users={unique_users} | "
            "attacks={attack_count} | attack_ratio={attack_ratio} | toxic_ratio={toxic_ratio} | "
            "attack_mean={attack_score_mean} | tox_mean={toxicity_score_mean} | "
            "streak={attack_streak_max}".format(**row)
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