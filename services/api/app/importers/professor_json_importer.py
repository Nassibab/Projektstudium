import os
import json
from pathlib import Path
from app.db.mongo import MongoDB
from app.mappers.comment_mapper import map_comment
from app.mappers.thread_mapper import map_thread


def import_json():
    mongo = MongoDB()

    threads_collection = mongo.collection("threads")
    comments_collection = mongo.collection("comments")

    folder_path = Path(__file__).resolve().parent.parent / "data"

    all_threads = []
    all_comments = []

    print("Importiere aus:", folder_path)

    for filename in os.listdir(folder_path):
        if not filename.endswith(".json"):
            continue

        file_path = folder_path / filename
        print("Datei:", file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict) or "threads" not in data:
            print(f"Überspringe (kein Thread-Format): {filename}")
            continue

        for thread in data["threads"]:
            thread_id = thread["thread_id"]

            all_threads.append(
                map_thread(
                    thread_id=thread_id,
                    title=thread.get("title"),
                    comments_count=len(thread.get("messages", [])),
                    source_platform="professor_dataset",
                    source_type="training/test",
                    extra={
                        "scenario_type": thread.get("scenario_type"),
                        "label_shitstorm": thread.get("label_shitstorm"),
                        "description": thread.get("description"),
                        "source_file": filename,
                        "is_long_thread":thread.get("is_long_thread"),
                    },
                )
            )

            for msg in thread.get("messages", []):
                all_comments.append(
                    map_comment(
                        comment_id=msg.get("id"),
                        thread_id=thread_id,
                        user=msg.get("login"),
                        text=msg.get("text"),
                        parent_id=msg.get("parent"),
                        created_at=msg.get("created"),
                        source_platform="professor_dataset",
                        source_type="training/test",
                        source_file=filename,
                        extra={
                            "subject": msg.get("subject"),
                            "synthetic": msg.get("synthetic"),
                            "synthetic_role": msg.get("synthetic_role"),
                            "toxicity_level": msg.get("toxicity_level"),
                            "target_user": msg.get("target_login"),
                        },
                    )
                )
    if all_threads:
        threads_collection.insert_many(all_threads)

    if all_comments:
        comments_collection.insert_many(all_comments)

    print("Threads:", threads_collection.count_documents({}))
    print("Comments:", comments_collection.count_documents({}))

    mongo.close()


if __name__ == "__main__":
    import_json()