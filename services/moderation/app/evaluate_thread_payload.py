from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.evaluation_window_report import collect_aggregated_windows
from app.moderation_warning_service import ModerationWarningService


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
    return thread_meta if isinstance(thread_meta, dict) else {}


def get_raw_comments(thread_data: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(thread_data.get("comments"), list):
        return thread_data["comments"]

    thread = thread_data.get("thread")
    if isinstance(thread, dict) and isinstance(thread.get("comments"), list):
        return thread["comments"]

    data = thread_data.get("data")
    if isinstance(data, dict) and isinstance(data.get("comments"), list):
        return data["comments"]

    raise ValueError("API-Response muss eine comments-Liste enthalten.")


def get_thread_id(thread_data: dict[str, Any], comments: list[dict[str, Any]]) -> str:
    thread_meta = get_thread_meta(thread_data)
    return str(
        thread_meta.get("thread_id")
        or thread_data.get("thread_id")
        or comments[0].get("thread_id")
        or "unknown_thread"
    )


def get_thread_size(thread_data: dict[str, Any], comments: list[dict[str, Any]]) -> int:
    thread_meta = get_thread_meta(thread_data)
    return int(
        thread_meta.get("comments_count")
        or thread_data.get("comments_count")
        or len(comments)
    )


def get_metric(raw: dict[str, Any], key: str, default: float = 0.0) -> float:
    if key in raw:
        return to_float(raw.get(key), default)

    llm_metrics = raw.get("llm_metrics")
    if isinstance(llm_metrics, dict):
        return to_float(llm_metrics.get(key), default)

    return default


def get_probability(raw: dict[str, Any], key: str, default: float = 0.0) -> float:
    if key in raw:
        return to_float(raw.get(key), default)

    ml_prediction = raw.get("ml_prediction")
    if isinstance(ml_prediction, dict):
        return to_float(ml_prediction.get(key), default)

    return default


def get_role(raw: dict[str, Any]) -> str:
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


def get_role_label(raw: dict[str, Any]) -> str:
    if raw.get("predicted_synthetic_role_label") is not None:
        return str(raw.get("predicted_synthetic_role_label"))

    ml_prediction = raw.get("ml_prediction")
    if isinstance(ml_prediction, dict):
        if ml_prediction.get("predicted_synthetic_role_label") is not None:
            return str(ml_prediction.get("predicted_synthetic_role_label"))

    if raw.get("synthetic_role") is not None:
        return str(raw.get("synthetic_role"))

    return ""


def build_llm_metrics(raw: dict[str, Any]) -> dict[str, Any]:
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


def prepare_comments_for_warning_service(thread_data: dict[str, Any]) -> list[dict[str, Any]]:
    raw_comments = get_raw_comments(thread_data)
    if not raw_comments:
        raise ValueError("comments-Liste ist leer.")

    comments = sorted(raw_comments, key=lambda item: str(item.get("created_at", "")))
    thread_meta = get_thread_meta(thread_data)
    thread_id = get_thread_id(thread_data, comments)
    thread_size = get_thread_size(thread_data, comments)

    login_total = Counter(str(comment.get("login", "")) for comment in comments)
    thread_user_count = len(login_total)
    thread_max_comments_by_one_user = max(login_total.values()) if login_total else 0
    thread_single_comment_user_count = sum(1 for count in login_total.values() if count == 1)
    thread_mean_comments_per_user = thread_size / thread_user_count if thread_user_count else 0.0
    thread_max_user_share = thread_max_comments_by_one_user / thread_size if thread_size else 0.0
    thread_single_comment_user_share = thread_single_comment_user_count / thread_user_count if thread_user_count else 0.0

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
        role_label = str(get_role_label(raw)).lower()

        is_attacking = int(
            to_int(llm_metrics.get("is_attacking")) == 1
            or attack_score >= 5
            or role_label == "attack"
            or str(get_role(raw)) == "5"
        )

        previous_comments_count = to_int(raw.get("num_previous_comments"), index - 1)
        time_since_thread_start = (created_at - first_created_at).total_seconds()
        time_since_previous_comment = 0.0 if index == 1 else (created_at - previous_created_at).total_seconds()
        previous_created_at = created_at

        login_count_total = login_total.get(login, 0)
        user_count_before = user_seen_count[login]
        user_previous_thread_share = user_count_before / (index - 1) if index > 1 else 0.0
        user_seen_count[login] += 1

        previous_comment_attack = previous_attack_flags[-1] if previous_attack_flags else 0
        prev_attack_count = to_int(raw.get("prev_attack_count"), sum(previous_attack_flags))
        prev_attack_rate = to_float(
            raw.get("prev_attack_rate"),
            sum(previous_attack_flags) / len(previous_attack_flags) if previous_attack_flags else 0.0,
        )
        prev_toxicity_score_mean = to_float(
            raw.get("prev_toxicity_score_mean"),
            sum(previous_toxicity_scores) / len(previous_toxicity_scores) if previous_toxicity_scores else 0.0,
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
            "thread_position_rel": to_float(raw.get("thread_position_rel"), index / thread_size if thread_size else 0.0),
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
            "num_children": to_int(raw.get("num_children"), children_by_parent.get(comment_id, 0)),
            "parent_is_root": to_int(raw.get("parent_is_root"), int(parent_id == root_comment_id)),
            "is_target_login_numeric": int(str(raw.get("target_login")).isdigit()) if raw.get("target_login") is not None else 0,
            "thread_user_count": thread_user_count,
            "thread_comment_count": thread_size,
            "thread_mean_comments_per_user": thread_mean_comments_per_user,
            "thread_max_comments_by_one_user": thread_max_comments_by_one_user,
            "thread_single_comment_user_count": thread_single_comment_user_count,
            "thread_max_user_share": thread_max_user_share,
            "thread_single_comment_user_share": thread_single_comment_user_share,
            "log_time_since_thread_start": math.log1p(max(0.0, time_since_thread_start)),
            "log_time_since_previous_comment": math.log1p(max(0.0, time_since_previous_comment)),
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
            "target_response_context_score": to_float(raw.get("target_response_context_score")),
            "source_file": raw.get("source_file", thread_meta.get("source_file")),
            "source_platform": raw.get("source_platform", thread_data.get("platform")),
            "source_type": raw.get("source_type", thread_meta.get("source_type")),
            "thread_title": raw.get("thread_title", thread_meta.get("title")),
            "scenario_type": raw.get("scenario_type", thread_meta.get("scenario_type")),
            "label_shitstorm": raw.get("label_shitstorm", thread_meta.get("label_shitstorm")),
            "toxicity_level": raw.get("toxicity_level"),
            "predicted_synthetic_role": get_role(raw),
            "predicted_synthetic_role_label": get_role_label(raw),
            "prob_class_1": to_float(ml_prediction.get("prob_class_1", get_probability(raw, "prob_class_1"))),
            "prob_class_2": to_float(ml_prediction.get("prob_class_2", get_probability(raw, "prob_class_2"))),
            "prob_class_3": to_float(ml_prediction.get("prob_class_3", get_probability(raw, "prob_class_3"))),
            "prob_class_4": to_float(ml_prediction.get("prob_class_4", get_probability(raw, "prob_class_4"))),
            "prob_class_5": to_float(ml_prediction.get("prob_class_5", get_probability(raw, "prob_class_5"))),
            "prob_class_6": to_float(ml_prediction.get("prob_class_6", get_probability(raw, "prob_class_6"))),
            "prob_class_7": to_float(ml_prediction.get("prob_class_7", get_probability(raw, "prob_class_7"))),
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


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def evaluate_thread_payload(
    thread_data: dict[str, Any],
    output_dir: str | Path = "evaluation_results",
    run_name: str | None = None,
    window_minutes: int = 5,
    rolling_window_size: int = 5,
    min_history: int = 3,
    z_watch: float = 1.0,
    z_full: float = 3.0,
    cusum_reference: float = 0.5,
    cusum_watch: float = 1.5,
    cusum_full: float = 5.0,
    watch_threshold: float = 0.20,
    warning_threshold: float = 0.40,
    critical_threshold: float = 0.60,
) -> dict[str, Any]:
    if min_history > rolling_window_size:
        raise ValueError("min_history darf nicht größer als rolling_window_size sein.")
    if not (watch_threshold <= warning_threshold <= critical_threshold):
        raise ValueError("Erwartet: watch_threshold <= warning_threshold <= critical_threshold.")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    raw_comments = get_raw_comments(thread_data)
    if not raw_comments:
        raise ValueError("comments-Liste ist leer.")

    thread_meta = get_thread_meta(thread_data)
    thread_id = get_thread_id(thread_data, raw_comments)

    if run_name is None:
        run_name = safe_name(f"{thread_data.get('platform', 'platform')}_{thread_id}")
    else:
        run_name = safe_name(run_name)

    comments = prepare_comments_for_warning_service(thread_data)

    service = ModerationWarningService(
        window_minutes=window_minutes,
        rolling_window_size=rolling_window_size,
        min_history=min_history,
        z_watch=z_watch,
        z_full=z_full,
        cusum_reference=cusum_reference,
        cusum_watch=cusum_watch,
        cusum_full=cusum_full,
        watch_threshold=watch_threshold,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
    )

    if hasattr(service, "counter_speech_selector"):
        service.counter_speech_selector.should_generate_counter_speech = lambda *args, **kwargs: False

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
            "window_end": metrics.get("window_end", ""),
            "comment_count": metrics.get("comment_count", 0),
            "unique_users": metrics.get("unique_users", 0),
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
            "evaluation_status": prediction.get("evaluation_status", ""),
            "has_sufficient_history": prediction.get("has_sufficient_history", False),
            "warning_reason": (prediction.get("warning_decision", {}) or {}).get("reason", ""),
            "score_raw_0_1": prediction.get("score_raw_0_1", 0),
            "score_final_0_1": prediction.get("score_final_0_1", score_0_1),
            "aggression_cap_0_1": prediction.get("aggression_cap_0_1", 0),
            "cap_applied": prediction.get("cap_applied", False),
        }
        rows.append(row)
        raw_outputs.append(output)

    windows = collect_aggregated_windows(service)

    rows_csv_path = output_path / f"{run_name}_rows.csv"
    windows_csv_path = output_path / f"{run_name}_windows.csv"
    summary_json_path = output_path / f"{run_name}_summary.json"
    details_json_path = output_path / f"{run_name}_details.json"

    _write_csv(rows_csv_path, rows)
    _write_csv(windows_csv_path, windows)

    scoring_config = {
        "method": "rolling_z_cusum_aggression_cap_thresholds",
        "absolute_fallback": False,
        "aggression_cap": True,
        "warning_logic": "thresholds_on_final_aggression_capped_barometer",
        "window_minutes": window_minutes,
        "rolling_window_size": rolling_window_size,
        "min_history": min_history,
        "z_watch": z_watch,
        "z_full": z_full,
        "cusum_reference": cusum_reference,
        "cusum_watch": cusum_watch,
        "cusum_full": cusum_full,
        "watch_threshold": watch_threshold,
        "warning_threshold": warning_threshold,
        "critical_threshold": critical_threshold,
    }

    worst_level = max(
        (row["warning_level"] for row in rows),
        key=lambda level: LEVEL_ORDER.get(str(level), 0),
        default="normal",
    )
    final_row = rows[-1] if rows else {}
    max_score_row = max(rows, key=lambda row: row["score_0_100"], default={})

    summary = {
        "status": "success",
        "platform": thread_data.get("platform"),
        "thread_id": thread_id,
        "source_file": thread_meta.get("source_file"),
        "source_platform": thread_meta.get("source_platform"),
        "source_type": thread_meta.get("source_type"),
        "title": thread_meta.get("title"),
        "comments_count_api": thread_data.get("comments_count"),
        "comments_count_thread_meta": thread_meta.get("comments_count"),
        "comments_count_evaluated": len(comments),
        "windows_count_evaluated": len(windows),
        "final_warning_level": final_row.get("warning_level", "normal"),
        "final_evaluation_status": final_row.get("evaluation_status", ""),
        "worst_warning_level": worst_level,
        "final_score_0_1": final_row.get("score_0_1", 0.0),
        "final_score_0_100": final_row.get("score_0_100", 0.0),
        "max_score_0_100": max_score_row.get("score_0_100", 0.0),
        "max_score_comment_id": max_score_row.get("comment_id"),
        "max_score_warning_level": max_score_row.get("warning_level"),
        "label_shitstorm": thread_meta.get("label_shitstorm"),
        "scenario_type": thread_meta.get("scenario_type"),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    with summary_json_path.open("w", encoding="utf-8") as file:
        json.dump({"scoring_config": scoring_config, "summary": summary}, file, indent=2, ensure_ascii=False)

    with details_json_path.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "scoring_config": scoring_config,
                "summary": summary,
                "rows": rows,
                "windows": windows,
                "raw_outputs": raw_outputs,
            },
            file,
            indent=2,
            ensure_ascii=False,
        )

    return {
        "scoring_config": scoring_config,
        "summary": summary,
        "files": {
            "summary_json": str(summary_json_path),
            "details_json": str(details_json_path),
            "rows_csv": str(rows_csv_path),
            "windows_csv": str(windows_csv_path),
        },
        "rows": rows,
        "windows": windows,
    }
