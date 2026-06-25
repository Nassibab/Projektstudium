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

def get_bluesky_comments_for_prediction():
    comments = list(comments_collection.find(
        {"source_file": "bluesky"},
        {"_id": 0}
    ))

    threads = list(threads_collection.find(
        {"source_file": "bluesky"},
        {"_id": 0}
    ))

    llm_results = list(mongo.collection("llm_analysis_results").find(
        {"source_file": "bluesky"},
        {"_id": 0}
    ))

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
# ladet nur Kommentare mit LLM-Features zu genau einem Bluesky-Thread 
#------------------------------------------------------------------------------------
def get_bluesky_thread_for_prediction(thread_id: str):
    thread_id_values = [thread_id, str(thread_id)]

    # Falls thread_id in Mongo als Zahl gespeichert wurde
    if str(thread_id).isdigit():
        thread_id_values.append(int(thread_id))

    thread = threads_collection.find_one(
        {
            "source_file": "bluesky",
            "thread_id": {"$in": thread_id_values},
        },
        {"_id": 0},
    )

    comments = list(
        comments_collection.find(
            {
                "source_file": "bluesky",
                "thread_id": {"$in": thread_id_values},
            },
            {"_id": 0},
        ).sort("created_at", 1)
    )

    if not thread and not comments:
        return None

    llm_results = list(
        mongo.collection("llm_analysis_results").find(
            {
                "source_file": "bluesky",
                "thread_id": {"$in": [str(v) for v in thread_id_values]},
            },
            {"_id": 0},
        )
    )

    llm_by_comment_id = {
        str(r.get("comment_id")): r
        for r in llm_results
        if r.get("comment_id") is not None
    }

    result = []

    for c in comments:
        comment_id = str(c.get("comment_id"))
        llm = llm_by_comment_id.get(comment_id, {})

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

            # Wichtig für R / TF-IDF / Strukturfeatures
            "thread_title": thread.get("title") if thread else None,
            "comments_count": thread.get("comments_count") if thread else len(comments),

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
# ladet nur Kommentare mit LLM-Features zu genau einem Professor-Thread 
#------------------------------------------------------------------------------------


def get_professor_comments_for_analysis_by_thread(
    thread_id: str,
    source_file: str | None = None,
):
    thread_id_values = [thread_id]

    if str(thread_id).isdigit():
        thread_id_values.append(int(thread_id))

    comment_query = {
        "source_platform": "professor_dataset",
        "thread_id": {"$in": thread_id_values},
    }

    thread_query = {
        "source_platform": "professor_dataset",
        "thread_id": {"$in": thread_id_values},
    }

    llm_query = {
        "thread_id": {"$in": [str(v) for v in thread_id_values]},
    }

    if source_file:
        comment_query["source_file"] = source_file
        thread_query["source_file"] = source_file
        llm_query["source_file"] = source_file

    comments = list(comments_collection.find(comment_query, {"_id": 0}).sort("created_at", 1))
    threads = list(threads_collection.find(thread_query, {"_id": 0}))
    llm_results = list(mongo.collection("llm_analysis_results").find(llm_query, {"_id": 0}))

    if not comments:
        return None

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




def get_latest_moderation_thread(
    thread_id: str,
    platform: str,
    source_file: str | None = None,
):
    platform = platform.lower().strip()

    if platform == "bluesky":
        source_platform = "bluesky"
        ml_collection_name = "bluesky_prediction_comments_results"

    elif platform in ["professor", "professor_dataset"]:
        source_platform = "professor_dataset"
        ml_collection_name = "professor_test_comment_results"

    else:
        return {
            "error": "invalid_platform",
            "message": "platform must be either 'bluesky' or 'professor'",
        }

    thread_id_values = [thread_id, str(thread_id)]

    if str(thread_id).isdigit():
        thread_id_values.append(int(thread_id))

    # Duplikate entfernen, aber Reihenfolge behalten
    thread_id_values = list(dict.fromkeys(thread_id_values))

    ml_query = {
        "thread_id": {"$in": thread_id_values},
    }

    if source_file:
        ml_query["source_file"] = source_file

    ml_collection = mongo.collection(ml_collection_name)

    # Wichtig:
    # Falls ein Kommentar mehrfach analysiert wurde,
    # nehmen wir später pro comment_id nur den neuesten Eintrag.
    ml_results = list(
        ml_collection.find(ml_query).sort([
            ("analysis_saved_at", -1),
            ("_id", -1),
        ])
    )

    if not ml_results:
        return None

    # Sicherheitsprüfung für Professor:
    # Professor thread_ids können in mehreren source_files vorkommen.
    if not source_file and platform in ["professor", "professor_dataset"]:
        source_files = {
            r.get("source_file")
            for r in ml_results
            if r.get("source_file") is not None
        }

        if len(source_files) > 1:
            return {
                "error": "ambiguous_thread",
                "message": (
                    f"thread_id={thread_id} exists in multiple source_files. "
                    "Please provide source_file as query parameter."
                ),
                "source_files": sorted(source_files),
            }

    # Pro comment_id nur den neuesten gespeicherten ML-Datensatz behalten.
    # Weil oben absteigend sortiert wurde, ist der erste Treffer pro Kommentar der aktuellste.
    latest_by_comment_id = {}

    for result in ml_results:
        comment_id = result.get("comment_id")

        if comment_id is None:
            continue

        comment_key = str(comment_id)

        if comment_key in latest_by_comment_id:
            continue

        clean_result = dict(result)
        clean_result.pop("_id", None)

        latest_by_comment_id[comment_key] = clean_result

    comments = list(latest_by_comment_id.values())

    if not comments:
        return None

    resolved_source_file = (
        source_file
        or comments[0].get("source_file")
    )

    # Kommentare wieder in Thread-Reihenfolge bringen.
    # Bevorzugt über thread_position_abs, sonst über created_at.
    def comment_sort_key(comment: dict):
        position = comment.get("thread_position_abs")

        if position is not None:
            try:
                return (
                    0,
                    float(position),
                    str(comment.get("created_at") or ""),
                    str(comment.get("comment_id") or ""),
                )
            except (TypeError, ValueError):
                pass

        return (
            1,
            str(comment.get("created_at") or ""),
            str(comment.get("comment_id") or ""),
        )

    comments.sort(key=comment_sort_key)

    thread_query = {
        "source_platform": source_platform,
        "thread_id": {"$in": thread_id_values},
    }

    if resolved_source_file:
        thread_query["source_file"] = resolved_source_file

    thread = threads_collection.find_one(
        thread_query,
        {"_id": 0},
    )

    return {
        "platform": platform,
        "source_collection": ml_collection_name,

        "thread": {
            "thread_id": thread.get("thread_id") if thread else thread_id,
            "source_file": thread.get("source_file") if thread else resolved_source_file,
            "source_platform": source_platform,
            "source_type": thread.get("source_type") if thread else comments[0].get("source_type"),
            "title": thread.get("title") if thread else comments[0].get("thread_title"),
            "comments_count": thread.get("comments_count") if thread else len(comments),
            "scenario_type": thread.get("scenario_type") if thread else None,
            "label_shitstorm": thread.get("label_shitstorm") if thread else None,
        },

        "comments_count": len(comments),
        "comments": comments,
    }



#1. Nimm die zuletzt gespeicherte ML-Prediction.
#2. Finde dazu den Original-Kommentar.
#3. Lade für genau diesen Kommentar die LLM-Metriken.
#4. Lade aus demselben Thread alle Kommentare davor.
#5. Gib bei den vorherigen Kommentaren nur den Text zurück.


def get_latest_comment_context_for_thread(
    thread_id: str,
    platform: str,
    source_file: str | None = None,
):
    platform = platform.lower().strip()

    if platform == "bluesky":
        source_platform = "bluesky"
        ml_collection_name = "bluesky_prediction_comments_results"

    elif platform in ["professor", "professor_dataset"]:
        source_platform = "professor_dataset"
        ml_collection_name = "professor_test_comment_results"

    else:
        return {
            "error": "invalid_platform",
            "message": "platform must be either 'bluesky' or 'professor'",
        }

    thread_id_values = [thread_id, str(thread_id)]

    if str(thread_id).isdigit():
        thread_id_values.append(int(thread_id))

    thread_id_values = list(dict.fromkeys(thread_id_values))

    query = {
        "thread_id": {"$in": thread_id_values},
    }

    if source_file:
        query["source_file"] = source_file

    collection = mongo.collection(ml_collection_name)

    # Alle gespeicherten Analyse-Kommentare zu genau diesem Thread laden.
    # Quelle ist je nach platform entweder:
    # - bluesky_prediction_comments_results
    # - professor_test_comment_results
    results = list(
        collection.find(query).sort([
            ("analysis_saved_at", -1),
            ("_id", -1),
        ])
    )

    if not results:
        return {
            "error": "thread_not_found",
            "message": (
                f"No moderation analysis data found for "
                f"platform={platform}, thread_id={thread_id}"
            ),
        }

    # Sicherheitsprüfung:
    # Professor-Thread-IDs können in mehreren source_files vorkommen.
    if not source_file and platform in ["professor", "professor_dataset"]:
        source_files = {
            r.get("source_file")
            for r in results
            if r.get("source_file") is not None
        }

        if len(source_files) > 1:
            return {
                "error": "ambiguous_thread",
                "message": (
                    f"thread_id={thread_id} exists in multiple source_files. "
                    "Please provide source_file as query parameter."
                ),
                "source_files": sorted(source_files),
            }

    # Falls ein Kommentar mehrfach gespeichert wurde:
    # pro comment_id nur den neuesten Datensatz behalten.
    latest_by_comment_id = {}

    for r in results:
        comment_id = r.get("comment_id")

        if comment_id is None:
            continue

        comment_key = str(comment_id)

        if comment_key in latest_by_comment_id:
            continue

        clean = dict(r)
        clean.pop("_id", None)

        latest_by_comment_id[comment_key] = clean

    comments = list(latest_by_comment_id.values())

    if not comments:
        return {
            "error": "comment_not_found",
            "message": (
                f"No valid comments found for platform={platform}, "
                f"thread_id={thread_id}"
            ),
        }

    # Thread-Reihenfolge herstellen.
    # Wenn R thread_position_abs liefert, ist das am saubersten.
    # Sonst fallback auf created_at/comment_id.
    def comment_sort_key(comment: dict):
        position = comment.get("thread_position_abs")

        if position is not None:
            try:
                return (
                    0,
                    float(position),
                    str(comment.get("created_at") or ""),
                    str(comment.get("comment_id") or ""),
                )
            except (TypeError, ValueError):
                pass

        return (
            1,
            str(comment.get("created_at") or ""),
            str(comment.get("comment_id") or ""),
        )

    comments.sort(key=comment_sort_key)

    # Der letzte Kommentar im Thread-Kontext ist der aktuelle Kommentar
    # für die Moderation.
    latest_comment_raw = comments[-1]
    latest_comment_id = latest_comment_raw.get("comment_id")

    # Nur die Felder aus deinem gewünschten JSON ausgeben.
    moderation_comment_fields = [
        "comment_id",
        "thread_id",
        "source_file",
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
        "source_platform",
        "analysis_saved_at",

        "prob_class_1",
        "prob_class_2",
        "prob_class_3",
        "prob_class_4",
        "prob_class_5",
        "prob_class_6",
        "prob_class_7",
    ]

    latest_comment = {
        field: latest_comment_raw.get(field)
        for field in moderation_comment_fields
    }

    # Falls source_platform in alten Professor-Ergebnissen fehlt,
    # trotzdem sauber setzen.
    if latest_comment.get("source_platform") is None:
        latest_comment["source_platform"] = source_platform

    previous_comments = []

    for c in comments:
        if str(c.get("comment_id")) == str(latest_comment_id):
            break

        previous_comments.append({
            "comment_id": c.get("comment_id"),
            "login": c.get("login"),
            "created_at": c.get("created_at"),
            "text": c.get("text"),
        })

    return {
        "platform": platform,
        "source_collection": ml_collection_name,
        "thread_id": thread_id,
        "source_file": source_file or latest_comment.get("source_file"),

        # Genau der Kommentar im flachen Format aus deinem Beispiel
        "latest_comment": latest_comment,

        # Danach die vorherigen Kommentare aus demselben Thread
        "previous_comments_count": len(previous_comments),
        "previous_comments": previous_comments,
    }