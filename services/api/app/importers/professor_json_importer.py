import os
import json
from pathlib import Path
from app.db.mongo import MongoDB


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

        for thread in data.get("threads", []):
            thread_id = thread["thread_id"]

            all_threads.append({
                "thread_id": thread_id,
                "external_id": thread_id,
                "source_provider": "professor",
                "source_platform": "professor_dataset",
                "source_type": "training",
                "title": thread.get("title"),
                "scenario_type": thread.get("scenario_type"),
                "label_shitstorm": thread.get("label_shitstorm"),
                "description": thread.get("description"),
                "source_file": filename,
                "status": "raw",
            })

            for msg in thread.get("messages", []):
                all_comments.append({
                    "comment_id": msg.get("id"),
                    "message_id": msg.get("id"),
                    "thread_id": thread_id,
                    "parent": msg.get("parent"),
                    "login": msg.get("login"),
                    "subject": msg.get("subject"),
                    "text": msg.get("text"),
                    "created": msg.get("created"),
                    "synthetic": msg.get("synthetic"),
                    "synthetic_role": msg.get("synthetic_role"),
                    "toxicity_level": msg.get("toxicity_level"),
                    "target_login": msg.get("target_login"),
                    "source_provider": "professor",
                    "source_platform": "professor_dataset",
                    "source_type": "training",
                    "source_file": filename,
                    "status": "raw",
                })

    if all_threads:
        threads_collection.insert_many(all_threads)

    if all_comments:
        comments_collection.insert_many(all_comments)

    print("Threads:", threads_collection.count_documents({}))
    print("Comments:", comments_collection.count_documents({}))

    mongo.close()


if __name__ == "__main__":
    import_json()