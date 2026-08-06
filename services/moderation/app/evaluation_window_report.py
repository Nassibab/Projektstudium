import csv


def collect_aggregated_windows(service):
    """
    Sammelt alle final aggregierten Fenster aus dem WindowStore.

    - Pro 5-Minuten-Fenster wird genau einmal aggregiert.
    - Es werden die finalen Fensterwerte nach Verarbeitung aller Kommentare ausgegeben.
    """
    rows = []

    for (thread_id, window_start), comments in service.store.windows.items():
        metrics = service.aggregator.aggregate(thread_id, window_start)

        row = {
            "thread_id": thread_id,
            "window_start": metrics.get("window_start"),
            "window_end": metrics.get("window_end"),

            # Aktivität / Frequenz
            "comment_count": metrics.get("comment_count"),
            "unique_users": metrics.get("unique_users"),
            "dominant_user_ratio": metrics.get("dominant_user_ratio"),

            # Thread-Kontext
            "thread_user_count": metrics.get("thread_user_count"),
            "thread_comment_count": metrics.get("thread_comment_count"),
            "thread_max_user_share": metrics.get("thread_max_user_share"),

            # Aggression
            "attack_count": metrics.get("attack_count"),
            "attack_ratio": metrics.get("attack_ratio"),
            "attack_score_mean": metrics.get("attack_score_mean"),
            "attack_score_max": metrics.get("attack_score_max"),

            # Toxizität
            "toxic_count": metrics.get("toxic_count"),
            "toxic_ratio": metrics.get("toxic_ratio"),
            "toxicity_score_mean": metrics.get("toxicity_score_mean"),
            "toxicity_score_max": metrics.get("toxicity_score_max"),

            # Negative Sprache
            "insult_comment_count": metrics.get("insult_comment_count"),
            "insult_ratio": metrics.get("insult_ratio"),
            "insult_count_sum": metrics.get("insult_count_sum"),
            "swearword_comment_count": metrics.get("swearword_comment_count"),
            "swearword_ratio": metrics.get("swearword_ratio"),
            "negative_word_count_mean": metrics.get("negative_word_count_mean"),

            # Dynamik
            "recent_attack_rate_3_mean": metrics.get("recent_attack_rate_3_mean"),
            "recent_attack_rate_5_mean": metrics.get("recent_attack_rate_5_mean"),
            "attack_streak_max": metrics.get("attack_streak_max"),
            "reply_after_attack_ratio": metrics.get("reply_after_attack_ratio"),

            # Fokus / Personalisierung
            "direct_address_mean": metrics.get("direct_address_mean"),
            "accusation_marker_mean": metrics.get("accusation_marker_mean"),
            "mockery_marker_mean": metrics.get("mockery_marker_mean"),
            "target_recently_attacked_ratio": metrics.get("target_recently_attacked_ratio"),
        }

        rows.append(row)

    rows.sort(key=lambda row: (str(row["thread_id"]), str(row["window_start"])))
    return rows


def print_aggregated_windows_table(rows):
    if not rows:
        print("\nKeine aggregierten Fenster vorhanden.")
        return

    columns = [
        "window_start",
        "comment_count",
        "unique_users",
        "attack_count",
        "attack_ratio",
        "toxic_ratio",
        "attack_score_mean",
        "toxicity_score_mean",
        "recent_attack_rate_5_mean",
        "attack_streak_max",
        "target_recently_attacked_ratio",
        "reply_after_attack_ratio",
    ]

    print("\n" + "=" * 120)
    print("AGGREGIERTE FENSTER")
    print("=" * 120)

    widths = {}
    for column in columns:
        widths[column] = max(
            len(column),
            max(len(str(row.get(column, ""))) for row in rows)
        )

    header = " | ".join(column.ljust(widths[column]) for column in columns)
    separator = "-+-".join("-" * widths[column] for column in columns)

    print(header)
    print(separator)

    for row in rows:
        line = " | ".join(
            str(row.get(column, "")).ljust(widths[column])
            for column in columns
        )
        print(line)


def save_aggregated_windows_csv(rows, output_dir, thread_file):
    if not rows:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{thread_file.stem}_aggregated_windows.csv"

    columns = list(rows[0].keys())

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    return output_path


def print_and_save_aggregated_windows(service, output_dir, thread_file):
    rows = collect_aggregated_windows(service)

    print_aggregated_windows_table(rows)

    csv_path = save_aggregated_windows_csv(
        rows=rows,
        output_dir=output_dir,
        thread_file=thread_file,
    )

    if csv_path:
        print(f"\nAggregierte Fenster gespeichert unter: {csv_path}")

    return csv_path