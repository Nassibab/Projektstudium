from app.db.mongo import MongoDB


def init_database():
    db = MongoDB()

    db.collection("threads").create_index("external_id")
    db.collection("threads").create_index("source")

    db.collection("comments").create_index("thread_id")
    db.collection("comments").create_index("created_at")

    db.collection("analysis_results").create_index("thread_id")
    db.collection("analysis_results").create_index("risk_score")

    db.collection("moderation_suggestions").create_index("analysis_result_id")

    db.collection("alerts").create_index("thread_id")
    db.collection("alerts").create_index("status")

    db.close()
    print("MongoDB Collections und Indexe wurden erstellt.")


if __name__ == "__main__":
    init_database()
