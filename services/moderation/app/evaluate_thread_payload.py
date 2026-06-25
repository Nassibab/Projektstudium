# app/evaluate_thread_payload.py

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.evaluation_window_json_report import save_window_report_json
from app.moderation_warning_service import ModerationWarningService


LEVEL_ORDER = {
    "normal": 0,
    "watch": 1,
    "warning": 2,
    "critical": 3,
}

ROLE_LABELS = {
    "1": "root",
    "2": "meta",
    "3": "discussion",
    "4": "counter_speech",
    "5": "attack",
    "6": "target_response",
    "7": "deescalation",
}

STANDARD_REQUIRED_FIELDS = [
    "comment_id",
    "thread_id",
    "login",
    "text",
    "created_at",
    "parent_id",
    "irony",
    "attack_score",
    "toxicity_score",
    "swearword_count",
    "negative_word_count",
    "insult_count",
    "direct_address_count",
    "imperative_count",
    "accusation_marker_count",
    "mockery_marker_count",
    "is_attacking",
    "reply_depth",
    "parent_is_root",
    "num_children",
    "thread_position_abs",
    "thread_position_rel",
    "num_previous_comments",
    "prev_attack_rate",
    "prev_toxicity_score_mean",
    "prev_attack_count",
    "prev_toxicity_score_max",
    "prev_attack_score_max",
    "recent_attack_rate_3",
    "recent_attack_rate_5",
    "attack_streak_current",
    "target_recently_attacked",
    "reply_after_attack",
    "target_response_context_score",
    "predicted_synthetic_role",
    "predicted_synthetic_role_label",
    "prob_class_1",
    "prob_class_2",
    "prob_class_3",
    "prob_class_4",
    "prob_class_5",
    "prob_class_6",
    "prob_class_7",
]


NUMERIC_FIELDS = {
    "irony",
    "attack_score",
    "toxicity_score",
    "swearword_count",
    "negative_word_count",
    "insult_count",
    "direct_address_count",
    "imperative_count",
    "accusation_marker_count",
    "mockery_marker_count",
    "thread_position_rel",
    "prev_attack_rate",
    "prev_toxicity_score_mean",
    "prev_toxicity_score_max",
    "prev_attack_score_max",
    "recent_attack_rate_3",
    "recent_attack_rate_5",
    "target_response_context_score",
    "prob_class_1",
    "prob_class_2",
    "prob_class_3",
    "prob_class_4",
    "prob_class_5",
    "prob_class_6",
    "prob_class_7",
}

INTEGER_FIELDS = {
    "is_attacking",
    "reply_depth",
    "parent_is_root",
    "num_children",
    "thread_position_abs",
    "num_previous_comments",
    "prev_attack_count",
    "attack_streak_current",
    "target_recently_attacked",
    "reply_after_attack",
}


METRIC_KEYS = [
    "irony",
    "attack_score",
    "toxicity_score",
    "swearword_count",
    "negative_word_count",
    "insult_count",
    "direct_address_count",
    "imperative_count",
    "accusation_marker_count",
    "mockery_marker_count",
]

PROBABILITY_KEYS = [
    "prob_class_1",
    "prob_class_2",
    "prob_class_3",
    "prob_class_4",
    "prob_class_5",
    "prob_class_6",
    "prob_class_7",
]


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
        ("unique_users", "users"),
        ("attack_count", "attacks"),
        ("attack_ratio", "attack_ratio"),
        ("toxic_ratio", "toxic_ratio"),
        ("attack_probability_mean", "p_attack"),
        ("freq", "freq"),
        ("aggr", "aggr"),
        ("dyn", "dyn"),
        ("focus", "focus"),
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


def nested_get(raw: dict[str, Any], container_key: str, key: str) -> Any:
    container = raw.get(container_key)

    if isinstance(container, dict):
        return container.get(key)

    return None


def metric_value(raw: dict[str, Any], key: str, default: float = 0.0) -> float:
    if key in raw:
        return to_float(raw.get(key), default)

    nested_value = nested_get(raw, "llm_metrics", key)
    if nested_value is not None:
        return to_float(nested_value, default)

    return default


def prediction_value(raw: dict[str, Any], key: str, default: Any = None) -> Any:
    if key in raw:
        return raw.get(key)

    nested_value = nested_get(raw, "ml_prediction", key)
    if nested_value is not None:
        return nested_value

    return default


def get_predicted_role(raw: dict[str, Any]) -> str:
    role = prediction_value(raw, "predicted_synthetic_role")

    if role is None:
        role = raw.get("synthetic_role")

    if role is None:
        return ""

    return str(role)


def get_predicted_role_label(raw: dict[str, Any], role: str) -> str:
    label = prediction_value(raw, "predicted_synthetic_role_label")

    if label is not None:
        return str(label)

    return ROLE_LABELS.get(str(role), "")


def is_attack_comment(raw: dict[str, Any], attack_score: float, role: str, role_label: str) -> int:
    if raw.get("is_attacking") is not None:
        return int(to_int(raw.get("is_attacking"), 0) == 1)

    llm_is_attacking = nested_get(raw, "llm_metrics", "is_attacking")
    if llm_is_attacking is not None:
        return int(to_int(llm_is_attacking, 0) == 1)

    return int(
        attack_score >= 5
        or str(role) == "5"
        or str(role_label).lower() == "attack"
    )


def calculate_previous_attack_streak(previous_attack_flags: list[int]) -> int:
    streak = 0

    for flag in reversed(previous_attack_flags):
        if flag != 1:
            break
        streak += 1

    return streak


def prepare_comments_for_warning_service(
    thread_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Bereitet Kommentare für den Service im neuen Standardformat vor.

    Die Evaluation soll denselben Inputpfad nutzen wie /moderation/warning.
    Deshalb werden keine alten Analyse-R-Featurefelder mehr erzeugt.
    Diese Funktion sortiert nur, füllt fehlende Standardfelder konservativ auf
    und erhält alle neuen Standardvariablen direkt.
    """

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
    thread_size = int(
        thread_meta.get("comments_count")
        or thread_data.get("comments_count")
        or len(comments)
    )

    root_comment_id = str(
        thread_meta.get("root_comment_id")
        or thread_meta.get("root_id")
        or ""
    )

    if not root_comment_id:
        for raw in comments:
            candidate_comment_id = get_str_id(raw.get("comment_id", raw.get("id")))
            candidate_parent_id = get_str_id(raw.get("parent_id", raw.get("parent")), "")

            if not candidate_parent_id:
                root_comment_id = candidate_comment_id
                break

    if not root_comment_id:
        root_comment_id = get_str_id(
            comments[0].get("comment_id", comments[0].get("id")),
            thread_id,
        )

    children_by_parent: dict[str, int] = {}
    for raw in comments:
        parent_id = get_str_id(raw.get("parent_id", raw.get("parent")), "")
        if parent_id:
            children_by_parent[parent_id] = children_by_parent.get(parent_id, 0) + 1

    previous_attack_flags: list[int] = []
    previous_toxicity_scores: list[float] = []
    previous_attack_scores: list[float] = []

    prepared: list[dict[str, Any]] = []

    for index, raw in enumerate(comments, start=1):
        comment_id = get_str_id(raw.get("comment_id", raw.get("id")), f"comment_{index}")
        parent_id = get_str_id(raw.get("parent_id", raw.get("parent")), "")

        attack_score = metric_value(raw, "attack_score", 1.0)
        toxicity_score = metric_value(raw, "toxicity_score", 1.0)

        role = get_predicted_role(raw)
        role_label = get_predicted_role_label(raw, role)
        is_attacking = is_attack_comment(raw, attack_score, role, role_label)

        previous_comment_count = to_int(raw.get("num_previous_comments"), index - 1)
        prev_attack_count = to_int(raw.get("prev_attack_count"), sum(previous_attack_flags))
        prev_attack_rate = to_float(
            raw.get("prev_attack_rate"),
            sum(previous_attack_flags) / len(previous_attack_flags)
            if previous_attack_flags
            else 0.0,
        )
        prev_toxicity_score_mean = to_float(
            raw.get("prev_toxicity_score_mean"),
            sum(previous_toxicity_scores) / len(previous_toxicity_scores)
            if previous_toxicity_scores
            else 1.0,
        )
        prev_toxicity_score_max = to_float(
            raw.get("prev_toxicity_score_max"),
            max(previous_toxicity_scores)
            if previous_toxicity_scores
            else 1.0,
        )
        prev_attack_score_max = to_float(
            raw.get("prev_attack_score_max"),
            max(previous_attack_scores)
            if previous_attack_scores
            else 1.0,
        )

        recent_3_flags = previous_attack_flags[-3:]
        recent_5_flags = previous_attack_flags[-5:]
        recent_attack_rate_3 = to_float(
            raw.get("recent_attack_rate_3"),
            sum(recent_3_flags) / len(recent_3_flags)
            if recent_3_flags
            else 0.0,
        )
        recent_attack_rate_5 = to_float(
            raw.get("recent_attack_rate_5"),
            sum(recent_5_flags) / len(recent_5_flags)
            if recent_5_flags
            else 0.0,
        )

        previous_streak = calculate_previous_attack_streak(previous_attack_flags)
        attack_streak_current = to_int(
            raw.get("attack_streak_current"),
            previous_streak + 1 if is_attacking else 0,
        )

        standard_comment = {
            "comment_id": comment_id,
            "thread_id": get_str_id(raw.get("thread_id"), thread_id),
            "source_file": raw.get("source_file", thread_meta.get("source_file")),
            "login": str(raw.get("login", "")),
            "text": raw.get("text", ""),
            "created_at": raw.get("created_at"),
            "parent_id": parent_id,

            "irony": metric_value(raw, "irony", 1.0),
            "attack_score": attack_score,
            "toxicity_score": toxicity_score,
            "swearword_count": metric_value(raw, "swearword_count", 0.0),
            "negative_word_count": metric_value(raw, "negative_word_count", 0.0),
            "insult_count": metric_value(raw, "insult_count", 0.0),
            "direct_address_count": metric_value(raw, "direct_address_count", 0.0),
            "imperative_count": metric_value(raw, "imperative_count", 0.0),
            "accusation_marker_count": metric_value(raw, "accusation_marker_count", 0.0),
            "mockery_marker_count": metric_value(raw, "mockery_marker_count", 0.0),
            "is_attacking": is_attacking,

            "reply_depth": to_int(raw.get("reply_depth"), 1 if parent_id else 0),
            "parent_is_root": to_int(raw.get("parent_is_root"), int(parent_id == root_comment_id)),
            "num_children": to_int(raw.get("num_children"), children_by_parent.get(comment_id, 0)),
            "thread_position_abs": to_int(raw.get("thread_position_abs"), index),
            "thread_position_rel": to_float(
                raw.get("thread_position_rel"),
                index / thread_size if thread_size else 0.0,
            ),
            "num_previous_comments": previous_comment_count,

            "prev_attack_rate": prev_attack_rate,
            "prev_toxicity_score_mean": prev_toxicity_score_mean,
            "prev_attack_count": prev_attack_count,
            "prev_toxicity_score_max": prev_toxicity_score_max,
            "prev_attack_score_max": prev_attack_score_max,
            "recent_attack_rate_3": recent_attack_rate_3,
            "recent_attack_rate_5": recent_attack_rate_5,
            "attack_streak_current": attack_streak_current,
            "target_recently_attacked": to_int(raw.get("target_recently_attacked"), 0),
            "reply_after_attack": to_int(
                raw.get("reply_after_attack"),
                previous_attack_flags[-1] if previous_attack_flags else 0,
            ),
            "target_response_context_score": to_float(raw.get("target_response_context_score"), 0.0),

            "predicted_synthetic_role": role,
            "predicted_synthetic_role_label": role_label,
            "source_platform": raw.get("source_platform", thread_data.get("platform")),
            "analysis_saved_at": raw.get("analysis_saved_at"),
            "prob_class_1": to_float(prediction_value(raw, "prob_class_1"), 0.0),
            "prob_class_2": to_float(prediction_value(raw, "prob_class_2"), 0.0),
            "prob_class_3": to_float(prediction_value(raw, "prob_class_3"), 0.0),
            "prob_class_4": to_float(prediction_value(raw, "prob_class_4"), 0.0),
            "prob_class_5": to_float(prediction_value(raw, "prob_class_5"), 0.0),
            "prob_class_6": to_float(prediction_value(raw, "prob_class_6"), 0.0),
            "prob_class_7": to_float(prediction_value(raw, "prob_class_7"), 0.0),

            # Optionale Metadaten bleiben erhalten, sind aber keine Pflichtfelder
            # des Aggregators mehr.
            "subject": raw.get("subject", ""),
            "target_login": raw.get("target_login"),
            "source_type": raw.get("source_type", thread_meta.get("source_type")),
            "thread_title": raw.get("thread_title", thread_meta.get("title")),
            "scenario_type": raw.get("scenario_type", thread_meta.get("scenario_type")),
            "label_shitstorm": raw.get("label_shitstorm", thread_meta.get("label_shitstorm")),
            "toxicity_level": raw.get("toxicity_level"),
            "raw_comment": raw,
        }

        missing = [field for field in STANDARD_REQUIRED_FIELDS if field not in standard_comment]
        if missing:
            raise KeyError(
                "Interner Fehler: Evaluation hat kein vollständiges Standardformat gebaut. "
                f"Fehlend: {missing}"
            )

        for field in NUMERIC_FIELDS:
            standard_comment[field] = to_float(standard_comment.get(field), 0.0)

        for field in INTEGER_FIELDS:
            standard_comment[field] = to_int(standard_comment.get(field), 0)

        prepared.append(standard_comment)

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
            "comment_id": comment.get("comment_id", ""),
            "created_at": comment.get("created_at", ""),
            "window_start": metrics.get("window_start", ""),
            "comment_count": metrics.get("comment_count", 0),
            "unique_users": metrics.get("unique_users", 0),
            "dominant_user_ratio": metrics.get("dominant_user_ratio", 0),
            "attack_count": metrics.get("attack_count", 0),
            "attack_ratio": metrics.get("attack_ratio", 0),
            "attack_score_mean": metrics.get("attack_score_mean", 0),
            "attack_score_mean_norm": metrics.get("attack_score_mean_norm", 0),
            "attack_probability_mean": metrics.get("attack_probability_mean", 0),
            "toxic_count": metrics.get("toxic_count", 0),
            "toxic_ratio": metrics.get("toxic_ratio", 0),
            "toxicity_score_mean": metrics.get("toxicity_score_mean", 0),
            "toxicity_score_mean_norm": metrics.get("toxicity_score_mean_norm", 0),
            "insult_ratio": metrics.get("insult_ratio", 0),
            "negative_word_count_mean": metrics.get("negative_word_count_mean", 0),
            "recent_attack_rate_3_mean": metrics.get("recent_attack_rate_3_mean", 0),
            "recent_attack_rate_5_mean": metrics.get("recent_attack_rate_5_mean", 0),
            "attack_streak_max": metrics.get("attack_streak_max", 0),
            "reply_after_attack_ratio": metrics.get("reply_after_attack_ratio", 0),
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
        "evaluation_mode": "new_standard_variables_direct",
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

    print("\n" + "=" * 120)
    print(f"Thread: {thread_id}")
    print(f"Platform: {thread_data.get('platform')}")
    print(f"Source file: {thread_meta.get('source_file')}")
    print(f"Title: {thread_meta.get('title')}")
    print(f"Evaluated comments: {len(comments)}")
    print("Input format: new_standard_variables_direct")
    print("=" * 120 + "\n")
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
                "prepared_comments_standard_format": comments,
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
