from collections import defaultdict
from app.db.mongo import MongoDB
from datetime import datetime, timezone


mongo = MongoDB()

threads_collection = mongo.collection("threads")
comments_collection = mongo.collection("comments")


def get_all_threads():
    threads = list(threads_collection.find(
    {
        "$or": [
            {"synced_to_neo4j": {"$exists": False}},
            {"synced_to_neo4j": False}
        ]
    },
    {"_id": 0}
))

    for thread in threads:
        thread["source_file"] = thread.get("source_file") or thread.get("source_platform", "unknown_source")

    return threads


def get_all_comments_grouped_by_thread():
    grouped = defaultdict(list)

    for comment in comments_collection.find({}):
        comment["_id"] = str(comment["_id"])

        source_file = comment.get("source_file") or comment.get("source_platform", "unknown_source")
        thread_id = comment.get("thread_id")

        if not thread_id:
            continue

        key = (source_file, thread_id)
        grouped[key].append(comment)

    return grouped

# ------------------------------------------------------------------------------
# Holt alle noch nicht analysierten Kommentare eines Threads durch LLM
# Bereits vorhandene Einträge in: llm_analysis_results werden übersprungen
# Dadurch werden keine unnötigen LLM-Aufrufe erzeugt.
# ------------------------------------------------------------------------------
    
def get_thread_comments_for_llm(
    thread_id: str,
    source_file: str,
    comment_ids: list[str] | None = None,
) -> list[dict]:

    query = {
        "thread_id": thread_id,
        "source_file": source_file,
    }

    if comment_ids:
        query["comment_id"] = {"$in": [str(cid) for cid in comment_ids]}

    already_analyzed = mongo.collection("llm_analysis_results").find(
        {
            "thread_id": thread_id,
            "source_file": source_file,
        },
        {
            "_id": 0,
            "comment_id": 1,
        },
    )

    analyzed_ids = {
        str(row.get("comment_id"))
        for row in already_analyzed
        if row.get("comment_id") is not None
    }

    comments = comments_collection.find(
        query,
        {
            "_id": 0,
            "comment_id": 1,
            "text": 1,
        },
    )

    by_id: dict[str, dict] = {}

    for c in comments:
        cid = str(c.get("comment_id"))
        text = c.get("text")

        if not cid or text is None:
            continue

        if cid in analyzed_ids:
            continue

        if cid not in by_id:
            by_id[cid] = {
                "comment_id": cid,
                "text": text,
            }

    if comment_ids:
        return [by_id[str(cid)] for cid in comment_ids if str(cid) in by_id]

    return list(by_id.values())

#---------------------------------------------------------------------------------------------
# Verwendet für die getrennte Endpoints /llm/analyze-professor und /llm/analyze-bluesky
#---------------------------------------------------------------------------------------------

def get_thread_keys_for_llm_by_platform(source_platform: str) -> list[dict]:
    return list(
        threads_collection.find(
            {"source_platform": source_platform},
            {"_id": 0, "thread_id": 1, "source_file": 1},
        )
    )
    
#--------------------------------------------------------------------------------------------
# Speichert die LLM-Analyseergebnisse pro Kommentar.
#    - Ein Kommentar wird eindeutig über thread_id + source_file + comment_id identifiziert.
#    - update_one(..., upsert=True) verhindert Duplikate.
#    - Wenn derselbe Kommentar erneut analysiert wird, werden die alten Werte aktualisiert.
#---------------------------------------------------------------------------------------------

def save_llm_analysis_results_per_comment(
    thread_id: str,
    results: list[dict],
    source_file: str | None = None,
) -> int:
    
    db = MongoDB()
    collection = db.collection("llm_analysis_results")

    saved_count = 0

    for item in results:
        scores = item.get("scores", {})
        comment_id = str(item.get("comment_id"))

        now = datetime.now(timezone.utc).isoformat()

        document = {
            "thread_id": thread_id,
            "source_file": source_file,
            "comment_id": comment_id,

            "irony": scores.get("irony"),
            "attack_score": scores.get("attack_score"),
            "toxicity_score": scores.get("toxicity_score"),
            "swearword_count": scores.get("swearword_count"),
            "negative_word_count": scores.get("negative_word_count"),
            "insult_count": scores.get("insult_count"),
            "direct_address_count": scores.get("direct_address_count"),
            "imperative_count": scores.get("imperative_count"),
            "accusation_marker_count": scores.get("accusation_marker_count"),
            "mockery_marker_count": scores.get("mockery_marker_count"),
            "is_attacking": scores.get("is_attacking"),

            "llm_analyzed_at": now,
        }

        collection.update_one(
            {
                "thread_id": thread_id,
                "source_file": source_file,
                "comment_id": comment_id,
            },
            {"$set": document},
            upsert=True,
        )

        saved_count += 1

    db.close()
    return saved_count

#-----------------------------------------------------------------------------------------
#    Baut den vollständigen Analysedatensatz für R.
#    Verbindet: comments Collection + threads Collection +llm_analysis_results Collection
#-----------------------------------------------------------------------------------------
def get_all_comments_for_analysis():
    
    comments = list(comments_collection.find(
    {"source_platform": "professor_dataset"},
    {"_id": 0}
))
    threads = list(threads_collection.find(
    {"source_platform": "professor_dataset"},
    {"_id": 0}
))
    llm_results = list(mongo.collection("llm_analysis_results").find({}, {"_id": 0}))

    threads_by_key = {
        (str(t.get("source_file")), str(t.get("thread_id"))): t
        for t in threads
    }

    llm_by_key = {
        (
            str(r.get("source_file")),
            str(r.get("thread_id")),
            str(r.get("comment_id")),
        ): r
        for r in llm_results
    }

    result = []

    for c in comments:
        key_thread = (str(c.get("source_file")), str(c.get("thread_id")))
        key_comment = (
            str(c.get("source_file")),
            str(c.get("thread_id")),
            str(c.get("comment_id")),
        )

        thread = threads_by_key.get(key_thread, {})
        llm = llm_by_key.get(key_comment, {})

        result.append({
            "comment_id": c.get("comment_id"),
            "thread_id": c.get("thread_id"),
            "source_file": c.get("source_file"),
            "parent_id": c.get("parent_id"),
            "login": c.get("user"),
            "text": c.get("text"),
            "created_at": c.get("created_at"),
            "source_platform": c.get("source_platform"),
            "source_type": c.get("source_type"),
            "synthetic": c.get("synthetic"),
            "synthetic_role": c.get("synthetic_role"),
            "toxicity_level": c.get("toxicity_level"),
            "target_login": c.get("target_user"),
            "thread_title": thread.get("title"),
            "comments_count": thread.get("comments_count"),
            "scenario_type": thread.get("scenario_type"),
            "label_shitstorm": thread.get("label_shitstorm"),

            "irony": llm.get("irony"),
            "attack_score": llm.get("attack_score"),
            "toxicity_score": llm.get("toxicity_score"),
            "swearword_count": llm.get("swearword_count"),
            "negative_word_count": llm.get("negative_word_count"),
            "insult_count": llm.get("insult_count"),
            "direct_address_count": llm.get("direct_address_count"),
            "imperative_count": llm.get("imperative_count"),
            "accusation_marker_count": llm.get("accusation_marker_count"),
            "mockery_marker_count": llm.get("mockery_marker_count"),
            "is_attacking": llm.get("is_attacking"),
        })

    return result

#-----------------------------------------------------------------------------------------
#  Baut den vollständigen Bluesky Analysedatensatz für R.
#-----------------------------------------------------------------------------------------

def get_bluesky_comments_for_prediction(thread_id: str | None = None):
    comment_query = {"source_file": "bluesky"}
    thread_query = {"source_file": "bluesky"}
    llm_query = {"source_file": "bluesky"}

    if thread_id:
        comment_query["thread_id"] = thread_id
        thread_query["thread_id"] = thread_id
        llm_query["thread_id"] = thread_id

    comments = list(comments_collection.find(comment_query, {"_id": 0}))

    threads = list(threads_collection.find(thread_query, {"_id": 0}))

    llm_results = list(mongo.collection("llm_analysis_results").find(llm_query, {"_id": 0}))

    threads_by_key = {
        (str(t.get("source_file")), str(t.get("thread_id"))): t
        for t in threads
    }

    llm_by_key = {
        (
            str(r.get("source_file")),
            str(r.get("thread_id")),
            str(r.get("comment_id")),
        ): r
        for r in llm_results
    }

    result = []

    for c in comments:
        key_thread = (str(c.get("source_file")), str(c.get("thread_id")))
        key_comment = (
            str(c.get("source_file")),
            str(c.get("thread_id")),
            str(c.get("comment_id")),
        )

        thread = threads_by_key.get(key_thread, {})
        llm = llm_by_key.get(key_comment, {})

        result.append({
            "comment_id": c.get("comment_id"),
            "thread_id": c.get("thread_id"),
            "source_file": c.get("source_file"),
            "parent_id": c.get("parent_id"),
            "login": c.get("user"),
            "text": c.get("text"),
            "created_at": c.get("created_at"),
            "source_platform": c.get("source_platform"),
            "source_type": c.get("source_type"),

            "thread_title": thread.get("title"),
            "comments_count": thread.get("comments_count"),

            "irony": llm.get("irony"),
            "attack_score": llm.get("attack_score"),
            "toxicity_score": llm.get("toxicity_score"),
            "swearword_count": llm.get("swearword_count"),
            "negative_word_count": llm.get("negative_word_count"),
            "insult_count": llm.get("insult_count"),
            "direct_address_count": llm.get("direct_address_count"),
            "imperative_count": llm.get("imperative_count"),
            "accusation_marker_count": llm.get("accusation_marker_count"),
            "mockery_marker_count": llm.get("mockery_marker_count"),
            "is_attacking": llm.get("is_attacking"),
        })

    return result


#------------------------------------------------------------------------------------
# Speichert die Professor-Test Ergebnisse aus der ML Analyse in MongoDB
# Speichert die Bluesky-Predictions Ergebnisse aus der ML Analyse in MongoDB
#------------------------------------------------------------------------------------

def save_analysis_results(payload: dict):
    db = MongoDB()

    bluesky_prediction_comments_results = payload.get(
        "bluesky_prediction_comments_results", []
    )
    bluesky_prediction_thread_results = payload.get(
        "bluesky_prediction_thread_results", []
    )
    bluesky_prediction_user_results = payload.get(
        "bluesky_prediction_user_results", []
    )
    bluesky_prediction_model_results = payload.get(
        "bluesky_prediction_model_results", []
    )
    professor_test_comment_results = payload.get(
        "professor_test_comment_results", [])
   
    professor_test_thread_results = payload.get(
        "professor_test_thread_results", [])
    
    professor_test_user_results = payload.get(
        "professor_test_user_results", [])
    
    professor_test_model_results = payload.get(
        "professor_test_model_results", [])

    if bluesky_prediction_comments_results:
        db.collection("bluesky_prediction_comments_results").delete_many({})
        db.collection("bluesky_prediction_comments_results").insert_many(
            bluesky_prediction_comments_results
        )

    if bluesky_prediction_thread_results:
        db.collection("bluesky_prediction_thread_results").delete_many({})
        db.collection("bluesky_prediction_thread_results").insert_many(
            bluesky_prediction_thread_results
        )

    if bluesky_prediction_user_results:
        db.collection("bluesky_prediction_user_results").delete_many({})
        db.collection("bluesky_prediction_user_results").insert_many(
            bluesky_prediction_user_results
        )

    if bluesky_prediction_model_results:
        db.collection("bluesky_prediction_model_results").delete_many({})
        db.collection("bluesky_prediction_model_results").insert_many(
            bluesky_prediction_model_results
        )
        
    if professor_test_comment_results:
        db.collection("professor_test_comment_results").delete_many({})
        db.collection("professor_test_comment_results").insert_many(professor_test_comment_results)

    if professor_test_thread_results:
        db.collection("professor_test_thread_results").delete_many({})
        db.collection("professor_test_thread_results").insert_many(professor_test_thread_results)

    if professor_test_user_results:
        db.collection("professor_test_user_results").delete_many({})
        db.collection("professor_test_user_results").insert_many(professor_test_user_results)

    if professor_test_model_results:
        db.collection("professor_test_model_results").insert_many(professor_test_model_results)

    db.close()

    return {
        "status": "success",
        "bluesky_prediction_comments_results": len(bluesky_prediction_comments_results),
        "bluesky_prediction_thread_results": len(bluesky_prediction_thread_results),
        "bluesky_prediction_user_results": len(bluesky_prediction_user_results),
        "bluesky_prediction_model_results": len(bluesky_prediction_model_results),
        "professor_test_comment_results": len(professor_test_comment_results),
        "professor_test_thread_results": len(professor_test_thread_results),
        "professor_test_user_results": len(professor_test_user_results),
        "professor_test_model_results": len(professor_test_model_results)
    }


#------------------------------------------------------------------------------------
# Liefert die eindeutigen Bluesky-Thread-IDs (für den Scheduler / Batch-Lauf).
#------------------------------------------------------------------------------------

def get_bluesky_thread_ids() -> list[str]:
    thread_ids = comments_collection.distinct("thread_id", {"source_file": "bluesky"})
    return [str(tid) for tid in thread_ids if tid is not None]


#------------------------------------------------------------------------------------
# Liefert die gespeicherten Bluesky-Predictions eines Threads (für die Moderation).
#------------------------------------------------------------------------------------

def get_bluesky_prediction_comments(thread_id: str) -> list[dict]:
    return list(
        mongo.collection("bluesky_prediction_comments_results").find(
            {"thread_id": thread_id},
            {"_id": 0},
        )
    )


#------------------------------------------------------------------------------------
# Speichert Moderations-Vorschläge pro Kommentar (Upsert über thread_id + comment_id).
#------------------------------------------------------------------------------------

def upsert_moderation_suggestions(thread_id: str, suggestions: list[dict]) -> int:
    db = MongoDB()
    collection = db.collection("moderation_suggestions")

    saved_count = 0

    for suggestion in suggestions:
        comment_id = str(suggestion.get("comment_id"))

        document = {
            **suggestion,
            "thread_id": thread_id,
            "comment_id": comment_id,
            "analysis_result_id": comment_id,
            "updated_at": datetime.utcnow(),
        }

        collection.update_one(
            {"thread_id": thread_id, "comment_id": comment_id},
            {
                "$set": document,
                "$setOnInsert": {"created_at": datetime.utcnow()},
            },
            upsert=True,
        )

        saved_count += 1

    db.close()
    return saved_count