import json
from app.db.mongo import MongoDB


def import_json():
    mongo = MongoDB()

    threads_collection = mongo.collection("threads")
    comments_collection = mongo.collection("comments")

    file_path = "/app/app/data/synthetic_shitstorm_dataset.json"

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    threads = data["threads"]

    for thread in threads:
        thread_doc = {
            "thread_id": thread["thread_id"],
            "title": thread["title"],
            "scenario_type": thread["scenario_type"],
            "label_shitstorm": thread["label_shitstorm"],
            "description": thread["description"]
        }

        threads_collection.insert_one(thread_doc)

        for msg in thread["comments"]:
            msg_doc = {
                "thread_id": thread["thread_id"],
                "message_id": msg["id"],
                "parent": msg["parent"],
                "login": msg["login"],
                "subject": msg.get("subject"),
                "text": msg["text"],
                "created": msg["created"],
                "synthetic": msg.get("synthetic"),
                "synthetic_role": msg.get("synthetic_role"),
                "toxicity_level": msg.get("toxicity_level"),
                "target_login": msg.get("target_login")
            }

            comments_collection.insert_one(msg_doc)

    mongo.close()
    print("✅ Import fertig!")


if __name__ == "__main__":
    import_json()