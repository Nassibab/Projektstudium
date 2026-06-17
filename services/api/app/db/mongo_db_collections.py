from app.db.mongo import MongoDB


def init_database():
    db = MongoDB()

    db.collection("threads").create_index("external_id")
    db.collection("threads").create_index("source")

    db.collection("comments").create_index("thread_id")
    db.collection("comments").create_index("created_at")

    db.collection("analysis_results").create_index("thread_id")
    db.collection("analysis_results").create_index("risk_score")

    db.collection("comment_analysis_results").create_index("comment_id")
    db.collection("comment_analysis_results").create_index("thread_id")
    db.collection("comment_analysis_results").create_index("login")
    db.collection("comment_analysis_results").create_index("predicted_synthetic_role")

    db.collection("thread_analysis_results").create_index("thread_id")
    db.collection("thread_analysis_results").create_index("thread_risk_score")
    db.collection("thread_analysis_results").create_index("thread_comment_count")

    db.collection("user_analysis_results").create_index("login")
    db.collection("user_analysis_results").create_index("login_count")
    db.collection("user_analysis_results").create_index("mean_toxicity_score")

    db.collection("model_results").create_index("model")
    db.collection("model_results").create_index("created_at")
    
    db.collection("llm_analysis_results").create_index("thread_id")

    db.collection("moderation_suggestions").create_index("analysis_result_id")

    db.collection("alerts").create_index("thread_id")
    db.collection("alerts").create_index("status")

    db.close()
    print("MongoDB Collections und Indexe wurden erstellt.")
