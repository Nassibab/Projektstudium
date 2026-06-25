# app/evaluate_thread_payload.py

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.moderation_warning_service import ModerationWarningService
from app.evaluation_window_json_report import save_window_report_json


LEVEL_ORDER = {
    "normal": 0,
    "watch": 1,
    "warning": 2,
    "critical": 3,
}


def safe_name(value: str) -> str:
    return "".join(
        char if char.isalnum() or char in ("-", "_") else "_"
        for char in str(value)
    )


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def get_str_id(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def parse_time(value: Any) -> datetime:
    value = str(value).strip()

    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")

    return datetime.fromisoformat(value)


def get_thread_meta(thread_data: dict[str, Any]) -> dict[str, Any]:
    thread_meta = thread_data.get("thread")

    if isinstance(thread_meta, dict):
        return thread_meta

    return {}


def get_thread_id(
    thread_data: dict[str, Any],
    comments: list[dict[str, Any]],
) -> str:
    thread_meta = get_thread_meta(thread_data)

    return str(
        thread_meta.get("thread_id")
        or thread_data.get("thread_id")
        or comments[0].get("thread_id")
        or "unknown_thread"
    )


def get_thread_size(
    thread_data: dict[str, Any],
    comments: list[dict[str, Any]],
) -> int:
    thread_meta = get_thread_meta(thread_data)

    return int(
        thread_meta.get("comments_count")
        or thread_data.get("comments_count")
        or len(comments)
    )


def get_metric(raw: dict[str, Any], key: str, default: float = 0.0) -> float:
    """
    Unterstützt beide Formen:
    1. Bluesky/API neu: raw["attack_score"]
    2. Professor alt: raw["llm_metrics"]["attack_score"]
    """

    if key in raw:
        return to_float(raw.get(key), default)

    llm_metrics = raw.get("llm_metrics")

    if isinstance(llm_metrics, dict):
        return to_float(llm_metrics.get(key), default)

    return default


def get_role(raw: dict[str, Any]) -> str:
    """
    Unterstützt neue und alte Role-Felder.
    """

    if raw.get("predicted_synthetic_role") is not None:
        return str(raw.get("predicted_synthetic_role"))

    ml_prediction = raw.get("ml_prediction")

    if isinstance(ml_prediction, dict):
        if ml_prediction.get("predicted_synthetic_role") is not None:
            return str(ml_prediction.get("predicted_synthetic_role"))

    if raw.get("synthetic_role") is not None:
        return str(raw.get("synthetic_role"))

    if raw.get("predicted_synthetic_role_label") is not None:
        return str(raw.get("predicted_synthetic_role_label"))

    return ""


def get_score(prediction: dict[str, Any]) -> tuple[float, float]:
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


def format_table(rows: list[dict[str, Any]]) -> str:
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
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    def make_line(values: list[str]) -> str:
        return " | ".join(
            value.ljust(widths[index])
            for index, value in enumerate(values)
        )

    separator = "-+-".join("-" * width for width in widths)

    lines = [make_line(headers), separator]
    lines.extend(make_line(row) for row in table_rows)

    return "\n".join(lines)


def build_llm_metrics(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Baut immer ein llm_metrics-Dict, auch wenn die API die Werte flach liefert.
    """

    if isinstance(raw.get("llm_metrics"), dict):
        return raw["llm_metrics"]

    return {
        "irony": get_metric(raw, "irony"),
        "attack_score": get_metric(raw, "attack_score"),
        "toxicity_score": get_metric(raw, "toxicity_score"),
        "swearword_count": get_metric(raw, "swearword_count"),
        "negative_word_count": get_metric(raw, "negative_word_count"),
        "insult_count": get_metric(raw, "insult_count"),
        "direct_address_count": get_metric(raw, "direct_address_count"),
        "imperative_count": get_metric(raw, "imperative_count"),
        "accusation_marker_count": get_metric(raw, "accusation_marker_count"),
        "mockery_marker_count": get_metric(raw, "mockery_marker_count"),
        "is_attacking": to_int(raw.get("is_attacking"), 0),
    }


def build_ml_prediction(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Baut immer ein ml_prediction-Dict, auch wenn die API die Prediction flach liefert.
    """

    if isinstance(raw.get("ml_prediction"), dict):
        return raw["ml_prediction"]

    return {
        "predicted_synthetic_role": raw.get("predicted_synthetic_role"),
        "predicted_synthetic_role_label": raw.get("predicted_synthetic_role_label"),
        "prob_class_1": raw.get("prob_class_1"),
        "prob_class_2": raw.get("prob_class_2"),
        "prob_class_3": raw.get("prob_class_3"),
        "prob_class_4": raw.get("prob_class_4"),
        "prob_class_5": raw.get("prob_class_5"),
        "prob_class_6": raw.get("prob_class_6"),
        "prob_class_7": raw.get("prob_class_7"),
    }


def prepare_comments_for_warning_service(
    thread_data: dict[str, Any],
) -> list[dict[str, Any]]:
    raw_comments = thread_data.get("comments")

    if not isinstance(raw_comments, list):
        raise ValueError("API-Response muss top-level 'comments' als Liste enthalten.")

    if not raw_comments:
        raise ValueError("comments-Liste ist leer.")

    comments = sorted(
        raw_comments,
        key=lambda item: str(item.get("created_at", "")),
    )

    thread_meta = get_thread_meta(thread_data)
    thread_id = get_thread_id(thread_data, comments)
    thread_size = get_thread_size(thread_data, comments)

    login_total = Counter(str(comment.get("login", "")) for comment in comments)

    thread_user_count = len(login_total)
    thread_max_comments_by_one_user = max(login_total.values()) if login_total else 0

    thread_single_comment_user_count = sum(
        1 for count in login_total.values()
        if count == 1
    )

    thread_mean_comments_per_user = (
        thread_size / thread_user_count
        if thread_user_count
        else 0.0
    )

    thread_max_user_share = (
        thread_max_comments_by_one_user / thread_size
        if thread_size
        else 0.0
    )

    thread_single_comment_user_share = (
        thread_single_comment_user_count / thread_user_count
        if thread_user_count
        else 0.0
    )

    root_comment_id = thread_id

    parent_by_comment_id: dict[str, str] = {}
    children_by_parent: dict[str, int] = defaultdict(int)

    for raw in comments:
        comment_id = get_str_id(raw.get("comment_id", raw.get("id")))
        parent_id = get_str_id(raw.get("parent_id", raw.get("parent")), "")

        parent_by_comment_id[comment_id] = parent_id

        if parent_id:
            children_by_parent[parent_id] += 1

    user_seen_count: dict[str, int] = defaultdict(int)

    previous_attack_flags: list[int] = []
    previous_toxicity_scores: list[float] = []
    previous_attack_scores: list[float] = []

    first_created_at = parse_time(comments[0]["created_at"])
    previous_created_at = first_created_at

    prepared: list[dict[str, Any]] = []

    for index, raw in enumerate(comments, start=1):
        comment_id = get_str_id(raw.get("comment_id", raw.get("id")))
        parent_id = get_str_id(raw.get("parent_id", raw.get("parent")), "")
        login = str(raw.get("login", ""))

        created_at = parse_time(raw["created_at"])

        llm_metrics = build_llm_metrics(raw)
        ml_prediction = build_ml_prediction(raw)

        attack_score = to_float(llm_metrics.get("attack_score"))
        toxicity_score = to_float(llm_metrics.get("toxicity_score"))

        is_attacking = int(
            to_int(llm_metrics.get("is_attacking")) == 1
            or attack_score >= 4
            or str(raw.get("predicted_synthetic_role_label", "")).lower() == "attack"
            or str(raw.get("synthetic_role", "")).lower() == "attack"
        )

        previous_comments_count = to_int(
            raw.get("num_previous_comments"),
            index - 1,
        )

        time_since_thread_start = (
            created_at - first_created_at
        ).total_seconds()

        if index == 1:
            time_since_previous_comment = 0.0
        else:
            time_since_previous_comment = (
                created_at - previous_created_at
            ).total_seconds()

        previous_created_at = created_at

        login_count_total = login_total.get(login, 0)
        user_count_before = user_seen_count[login]

        user_previous_thread_share = (
            user_count_before / (index - 1)
            if index > 1
            else 0.0
        )

        user_seen_count[login] += 1

        previous_comment_attack = (
            previous_attack_flags[-1]
            if previous_attack_flags
            else 0
        )

        prev_attack_count = to_int(
            raw.get("prev_attack_count"),
            sum(previous_attack_flags),
        )

        prev_attack_rate = to_float(
            raw.get("prev_attack_rate"),
            (
                sum(previous_attack_flags) / len(previous_attack_flags)
                if previous_attack_flags
                else 0.0
            ),
        )

        prev_toxicity_score_mean = to_float(
            raw.get("prev_toxicity_score_mean"),
            (
                sum(previous_toxicity_scores) / len(previous_toxicity_scores)
                if previous_toxicity_scores
                else 0.0
            ),
        )

        prev_toxicity_score_max = to_float(
            raw.get("prev_toxicity_score_max"),
            max(previous_toxicity_scores) if previous_toxicity_scores else 0.0,
        )

        prev_attack_score_max = to_float(
            raw.get("prev_attack_score_max"),
            max(previous_attack_scores) if previous_attack_scores else 0.0,
        )

        prepared_comment = {
            "is_long_thread": int(thread_size >= 100),
            "created_at": raw["created_at"],

            # Wichtig: Bluesky-IDs sind Strings. Nicht zu int konvertieren.
            "id": comment_id,
            "comment_id": comment_id,
            "thread_id": thread_id,

            "synthetic_role": get_role(raw),

            "irony": to_float(llm_metrics.get("irony")),
            "negative_word_count": to_float(llm_metrics.get("negative_word_count")),
            "insult_count": to_float(llm_metrics.get("insult_count")),
            "is_attacking": is_attacking,
            "attack_score": attack_score,
            "swearword_count": to_float(llm_metrics.get("swearword_count")),
            "toxicity_score": toxicity_score,
            "direct_address_count": to_float(llm_metrics.get("direct_address_count")),
            "imperative_count": to_float(llm_metrics.get("imperative_count")),
            "accusation_marker_count": to_float(llm_metrics.get("accusation_marker_count")),
            "mockery_marker_count": to_float(llm_metrics.get("mockery_marker_count")),

            "login": login,
            "text": raw.get("text", ""),
            "subject": raw.get("subject", ""),
            "parent": parent_id,
            "parent_id": parent_id,
            "target_login": raw.get("target_login"),

            "login_count": login_count_total,
            "login_percentage": login_count_total / thread_size if thread_size else 0.0,
            "frequency_group": raw.get("frequency_group", 1),
            "date_timestamp": created_at.timestamp(),

            "thread_position_abs": to_int(raw.get("thread_position_abs"), index),
            "thread_size": thread_size,
            "thread_position_rel": to_float(
                raw.get("thread_position_rel"),
                index / thread_size if thread_size else 0.0,
            ),
            "num_previous_comments": previous_comments_count,
            "is_thread_start": int(comment_id == root_comment_id or index == 1),
            "is_reply": int(bool(parent_id)),
            "previous_comment_exists": int(index > 1),

            "time_since_thread_start": time_since_thread_start,
            "time_since_previous_comment": time_since_previous_comment,

            "user_thread_comment_count_before": user_count_before,
            "user_thread_comment_count_total": login_count_total,
            "user_previous_thread_share": user_previous_thread_share,

            "reply_depth": to_int(raw.get("reply_depth"), 1 if parent_id else 0),
            "num_children": to_int(
                raw.get("num_children"),
                children_by_parent.get(comment_id, 0),
            ),
            "parent_is_root": to_int(
                raw.get("parent_is_root"),
                int(parent_id == root_comment_id),
            ),
            "is_target_login_numeric": (
                int(str(raw.get("target_login")).isdigit())
                if raw.get("target_login") is not None
                else 0
            ),

            "thread_user_count": thread_user_count,
            "thread_comment_count": thread_size,
            "thread_mean_comments_per_user": thread_mean_comments_per_user,
            "thread_max_comments_by_one_user": thread_max_comments_by_one_user,
            "thread_single_comment_user_count": thread_single_comment_user_count,
            "thread_max_user_share": thread_max_user_share,
            "thread_single_comment_user_share": thread_single_comment_user_share,

            "log_time_since_thread_start": math.log1p(
                max(0.0, time_since_thread_start)
            ),
            "log_time_since_previous_comment": math.log1p(
                max(0.0, time_since_previous_comment)
            ),

            "previous_comment_attack": previous_comment_attack,
            "prev_attack_count": prev_attack_count,
            "prev_attack_rate": prev_attack_rate,
            "prev_toxicity_score_mean": prev_toxicity_score_mean,
            "prev_toxicity_score_max": prev_toxicity_score_max,
            "prev_attack_score_max": prev_attack_score_max,

            "recent_attack_rate_3": to_float(raw.get("recent_attack_rate_3")),
            "recent_attack_rate_5": to_float(raw.get("recent_attack_rate_5")),
            "attack_streak_current": to_int(raw.get("attack_streak_current")),
            "target_recently_attacked": to_int(raw.get("target_recently_attacked")),
            "reply_after_attack": to_int(raw.get("reply_after_attack")),
            "target_response_context_score": to_float(
                raw.get("target_response_context_score")
            ),

            "source_file": raw.get("source_file", thread_meta.get("source_file")),
            "source_platform": raw.get(
                "source_platform",
                thread_data.get("platform"),
            ),
            "source_type": raw.get("source_type", thread_meta.get("source_type")),
            "thread_title": raw.get("thread_title", thread_meta.get("title")),
            "scenario_type": raw.get(
                "scenario_type",
                thread_meta.get("scenario_type"),
            ),
            "label_shitstorm": raw.get(
                "label_shitstorm",
                thread_meta.get("label_shitstorm"),
            ),
            "toxicity_level": raw.get("toxicity_level"),

            "predicted_synthetic_role": raw.get("predicted_synthetic_role"),
            "predicted_synthetic_role_label": raw.get("predicted_synthetic_role_label"),
            "analysis_saved_at": raw.get("analysis_saved_at"),

            "ml_prediction": ml_prediction,
            "llm_metrics": llm_metrics,
            "raw_comment": raw,
        }

        prepared.append(prepared_comment)

        previous_attack_flags.append(is_attacking)
        previous_toxicity_scores.append(toxicity_score)
        previous_attack_scores.append(attack_score)

    return prepared


def evaluate_thread_payload(
    thread_data: dict[str, Any],
    output_dir: str | Path = "evaluation_results",
    run_name: str | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_comments = thread_data.get("comments")

    if not isinstance(raw_comments, list) or not raw_comments:
        raise ValueError("API-Response muss top-level 'comments' als nicht-leere Liste enthalten.")

    thread_meta = get_thread_meta(thread_data)
    thread_id = get_thread_id(thread_data, raw_comments)

    if run_name is None:
        run_name = safe_name(f"{thread_data.get('platform', 'platform')}_{thread_id}")
    else:
        run_name = safe_name(run_name)

    comments = prepare_comments_for_warning_service(thread_data)

    service = ModerationWarningService(
        window_minutes=5,
        history_window_size=3,
    )

    # Keine LLM-Gegenrede während Evaluation.
    if hasattr(service, "counter_speech_selector"):
        service.counter_speech_selector.should_generate_counter_speech = (
            lambda *args, **kwargs: False
        )

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
            "comment_id": comment.get("comment_id", comment.get("id", "")),
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

    worst_level = max(
        (row["warning_level"] for row in rows),
        key=lambda level: LEVEL_ORDER.get(level, 0),
    )

    final_row = rows[-1]
    max_score_row = max(rows, key=lambda row: row["score_0_100"])

    summary = {
        "status": "success",
        "platform": thread_data.get("platform"),
        "source_collection": thread_data.get("source_collection"),
        "thread_id": thread_id,
        "source_file": thread_meta.get("source_file"),
        "source_platform": thread_meta.get("source_platform"),
        "source_type": thread_meta.get("source_type"),
        "title": thread_meta.get("title"),

        "comments_count_api": thread_data.get("comments_count"),
        "comments_count_thread_meta": thread_meta.get("comments_count"),
        "comments_count_evaluated": len(comments),

        "final_warning_level": final_row["warning_level"],
        "worst_warning_level": worst_level,
        "final_score_0_1": final_row["score_0_1"],
        "final_score_0_100": final_row["score_0_100"],

        "max_score_0_100": max_score_row["score_0_100"],
        "max_score_comment_id": max_score_row["comment_id"],
        "max_score_warning_level": max_score_row["warning_level"],

        "label_shitstorm": thread_meta.get("label_shitstorm"),
        "scenario_type": thread_meta.get("scenario_type"),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    print("\n" + "=" * 100)
    print(f"Thread: {thread_id}")
    print(f"Platform: {thread_data.get('platform')}")
    print(f"Source file: {thread_meta.get('source_file')}")
    print(f"Title: {thread_meta.get('title')}")
    print(f"Evaluated comments: {len(comments)}")
    print("=" * 100 + "\n")
    print(format_table(rows))

    summary_path = output_dir / f"{run_name}_summary.json"
    details_path = output_dir / f"{run_name}_details.json"

    with summary_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, ensure_ascii=False)

    with details_path.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "summary": summary,
                "rows": rows,
                "raw_outputs": raw_outputs,
            },
            file,
            indent=2,
            ensure_ascii=False,
        )

    window_report = save_window_report_json(
        service=service,
        output_dir=output_dir,
        run_name=run_name,
    )

    print("\nGespeichert:")
    print(f"- {summary_path}")
    print(f"- {details_path}")
    print(f"- {window_report['path']}")

    return {
        "summary": summary,
        "files": {
            "summary_json": str(summary_path),
            "details_json": str(details_path),
            "windows_json": window_report["path"],
        },
        "rows": rows,
        "windows": window_report["windows"],
    }