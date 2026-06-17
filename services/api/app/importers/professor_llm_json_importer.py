import json
from pymongo import UpdateOne
from app.db.mongo import MongoDB

from pathlib import Path

def import_llm_results_from_json_data(data):
    
    mongo = MongoDB()
    collection = mongo.collection("llm_analysis_results")

    operations = []
    skipped = 0

    for doc in data:
        if not isinstance(doc, dict):
            skipped += 1
            continue

        doc.pop("_id", None)

        source_file = doc.get("source_file")
        thread_id = str(doc.get("thread_id"))
        comment_id = str(doc.get("comment_id"))

        if not source_file or not thread_id or not comment_id:
            skipped += 1
            continue

        llm_doc = {
            "source_file": source_file,
            "thread_id": thread_id,
            "comment_id": comment_id,
            "irony": doc.get("irony"),
            "attack_score": doc.get("attack_score"),
            "toxicity_score": doc.get("toxicity_score"),
            "swearword_count": doc.get("swearword_count"),
            "negative_word_count": doc.get("negative_word_count"),
            "insult_count": doc.get("insult_count"),
            "direct_address_count": doc.get("direct_address_count"),
            "imperative_count": doc.get("imperative_count"),
            "accusation_marker_count": doc.get("accusation_marker_count"),
            "mockery_marker_count": doc.get("mockery_marker_count"),
            "is_attacking": doc.get("is_attacking"),
            "source_platform": doc.get("source_platform"),
            "source_type": doc.get("source_type"),
            "created_at": doc.get("created_at"),
        }

        operations.append(
            UpdateOne(
                {
                    "source_file": source_file,
                    "thread_id": thread_id,
                    "comment_id": comment_id,
                },
                {"$set": llm_doc},
                upsert=True,
            )
        )

    if not operations:
        return {
            "status": "error",
            "message": "Keine gültigen Dokumente gefunden",
            "skipped": skipped,
        }

    result = collection.bulk_write(operations)

    return {
        "status": "success",
        "received": len(data),
        "inserted": result.upserted_count,
        "updated": result.modified_count,
        "skipped": skipped,
    }
    

def import_professor_llm_dataset():
    file_path = Path(__file__).resolve().parent.parent / "data" / "LLM-Professor-Datasets.json"

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return import_llm_results_from_json_data(data)