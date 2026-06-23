#!/usr/bin/env python3
"""
Simple evaluation for one selected JSON thread.

Usage examples:
  python evaluate_one_thread.py
  python evaluate_one_thread.py --thread evaluation_threads/thread_03_slow_escalation_shitstorm.json
  python evaluate_one_thread.py --input evaluation_threads --output evaluation_one_thread_results

The script prints one table row per processed comment.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any
from evaluation_window_report import print_and_save_aggregated_windows

LEVEL_ORDER = {
    "normal": 0,
    "watch": 1,
    "warning": 2,
    "critical": 3,
}


def add_project_root_to_path() -> None:
    """Make `from app...` imports work when this file is run from inside app/."""
    script_path = Path(__file__).resolve()
    candidates = [
        script_path.parent,
        script_path.parent.parent,
        Path.cwd(),
        Path.cwd().parent,
    ]

    for candidate in candidates:
        if (candidate / "app" / "moderation_warning_service.py").exists():
            sys.path.insert(0, str(candidate))
            return

    # Last resort: if the script itself is inside app/, add its parent.
    if script_path.parent.name == "app":
        sys.path.insert(0, str(script_path.parent.parent))


def import_service_class():
    add_project_root_to_path()
    from app.moderation_warning_service import ModerationWarningService
    return ModerationWarningService


def find_default_input_dir() -> Path | None:
    candidates = [
        Path.cwd() / "evaluation_threads",
        Path.cwd() / "app" / "evaluation_threads",
        Path(__file__).resolve().parent / "evaluation_threads",
        Path(__file__).resolve().parent.parent / "evaluation_threads",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def load_thread(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if "comments" not in data or not isinstance(data["comments"], list):
        raise ValueError(f"{path.name}: expected top-level key 'comments' with a list")
    if not data["comments"]:
        raise ValueError(f"{path.name}: comments list is empty")

    return data


def choose_thread_file(input_dir: Path) -> Path:
    files = sorted(input_dir.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No JSON files found in {input_dir}")

    print("\nVerfügbare Test-Threads:\n")
    for index, file in enumerate(files, start=1):
        try:
            data = load_thread(file)
            scenario = data.get("scenario_name", file.stem)
            label = data.get("label_shitstorm", "?")
            num_comments = len(data.get("comments", []))
            print(f"{index:>2}. {file.name} | scenario={scenario} | label={label} | comments={num_comments}")
        except Exception:
            print(f"{index:>2}. {file.name}")

    while True:
        raw = input("\nWelche Nummer willst du testen? ").strip()
        try:
            selected = int(raw)
            if 1 <= selected <= len(files):
                return files[selected - 1]
        except ValueError:
            pass
        print("Bitte eine gültige Nummer eingeben.")


def get_score(prediction: dict[str, Any]) -> tuple[float, float]:
    """Return score as 0..1 and 0..100 while supporting slightly different key names."""
    if "barometer_score_0_1" in prediction:
        score_0_1 = float(prediction["barometer_score_0_1"])
    elif "score_0_1" in prediction:
        score_0_1 = float(prediction["score_0_1"])
    elif "shitstorm_barometer" in prediction:
        value = float(prediction["shitstorm_barometer"])
        score_0_1 = value / 100 if value > 1 else value
    else:
        score_0_1 = 0.0

    if "shitstorm_barometer" in prediction:
        score_0_100 = float(prediction["shitstorm_barometer"])
        if score_0_100 <= 1:
            score_0_100 *= 100
    else:
        score_0_100 = score_0_1 * 100

    return score_0_1, score_0_100


def get_dimension_scores(prediction: dict[str, Any]) -> dict[str, float]:
    scores = prediction.get("dimension_scores", {}) or {}
    return {
        "frequency": float(scores.get("frequency", 0.0)),
        "aggression_toxicity": float(scores.get("aggression_toxicity", 0.0)),
        "dynamics": float(scores.get("dynamics", 0.0)),
        "focus_personalization": float(scores.get("focus_personalization", 0.0)),
    }


def format_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    """Small dependency-free console table."""
    headers = [label for _, label in columns]
    table_rows = []

    for row in rows:
        values = []
        for key, _ in columns:
            value = row.get(key, "")
            if isinstance(value, float):
                value = f"{value:.3f}"
            values.append(str(value))
        table_rows.append(values)

    widths = [len(header) for header in headers]
    for row in table_rows:
        for i, value in enumerate(row):
            widths[i] = max(widths[i], len(value))

    def make_line(values: list[str]) -> str:
        return " | ".join(value.ljust(widths[i]) for i, value in enumerate(values))

    sep = "-+-".join("-" * width for width in widths)
    lines = [make_line(headers), sep]
    lines.extend(make_line(row) for row in table_rows)
    return "\n".join(lines)


def evaluate_one_thread(thread_file: Path, output_dir: Path) -> None:
    ModerationWarningService = import_service_class()

    service = ModerationWarningService(window_minutes=5, history_window_size=3)

    # No LLM calls during evaluation.
    if hasattr(service, "counter_speech_selector"):
        service.counter_speech_selector.should_generate_counter_speech = lambda *args, **kwargs: False

    thread_data = load_thread(thread_file)
    comments = sorted(thread_data["comments"], key=lambda item: item["created_at"])

    rows: list[dict[str, Any]] = []
    raw_outputs: list[dict[str, Any]] = []

    for index, comment in enumerate(comments, start=1):
        output = service.process_comment(comment)
        prediction = output["shitstorm_prediction"]
        metrics = output["current_window_metrics"]
        dimensions = get_dimension_scores(prediction)
        score_0_1, score_0_100 = get_score(prediction)

        row = {
            "nr": index,
            "comment_id": comment.get("id", ""),
            "created_at": comment.get("created_at", ""),
            "window_start": metrics.get("window_start", ""),
            "comment_count": metrics.get("comment_count", 0),
            "attack_count": metrics.get("attack_count", 0),
            "attack_ratio": metrics.get("attack_ratio", 0),
            "toxic_ratio": metrics.get("toxic_ratio", 0),
            "freq": dimensions["frequency"],
            "aggr": dimensions["aggression_toxicity"],
            "dyn": dimensions["dynamics"],
            "focus": dimensions["focus_personalization"],
            "score_0_1": score_0_1,
            "score_0_100": score_0_100,
            "warning_level": prediction.get("warning_level", ""),
        }
        rows.append(row)
        raw_outputs.append(output)

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{thread_file.stem}_results.csv"
    json_path = output_dir / f"{thread_file.stem}_details.json"

    columns = [
        ("nr", "#"),
        ("comment_id", "comment_id"),
        ("created_at", "created_at"),
        ("comment_count", "comments"),
        ("attack_count", "attacks"),
        ("attack_ratio", "attack_ratio"),
        ("toxic_ratio", "toxic_ratio"),
        ("freq", "freq"),
        ("aggr", "aggr"),
        ("dyn", "dyn"),
        ("focus", "focus"),
        ("score_0_1", "score"),
        ("score_0_100", "score_100"),
        ("warning_level", "level"),
    ]

    print("\n" + "=" * 100)
    print(f"Thread: {thread_file.name}")
    print(f"Scenario: {thread_data.get('scenario_name', '-')}")
    print(f"Label Shitstorm: {thread_data.get('label_shitstorm', '-')}")
    print("=" * 100 + "\n")
    print(format_table(rows, columns))

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with json_path.open("w", encoding="utf-8") as file:
        json.dump({"thread_file": str(thread_file), "rows": rows, "raw_outputs": raw_outputs}, file, indent=2, ensure_ascii=False)

    print("\nGespeichert:")
    print(f"- {csv_path}")
    print(f"- {json_path}")
    
    print_and_save_aggregated_windows(
        service=service,
        output_dir=output_dir,
        thread_file=thread_file,
    )



def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate exactly one JSON thread and print one result row per comment.")
    parser.add_argument("--input", type=Path, default=None, help="Folder containing JSON thread files")
    parser.add_argument("--thread", type=Path, default=None, help="Specific JSON thread file to evaluate")
    parser.add_argument("--output", type=Path, default=Path("evaluation_one_thread_results"), help="Output folder")
    args = parser.parse_args()

    if args.thread is not None:
        thread_file = args.thread
    else:
        input_dir = args.input or find_default_input_dir()
        if input_dir is None:
            raise FileNotFoundError("Could not find evaluation_threads folder. Use --input path/to/evaluation_threads.")
        thread_file = choose_thread_file(input_dir)

    if not thread_file.exists():
        raise FileNotFoundError(thread_file)

    evaluate_one_thread(thread_file, args.output)



if __name__ == "__main__":
    main()
