from app.db.mongo import MongoDB
from app.db.neo4j import get_driver

mongo = MongoDB()
db = mongo.db


def get_thread_report():
    total_threads = db["threads"].count_documents({})

    unique_threads = list(db["threads"].aggregate([
        {"$group": {"_id": "$thread_id"}},
        {"$count": "count"}
    ]))

    unique_threads = unique_threads[0]["count"] if unique_threads else 0

    duplicates = total_threads - unique_threads

    with get_driver().session() as session:
        neo_threads = session.run(
            "MATCH (t:Thread) RETURN count(t) AS c"
        ).single()["c"]

        neo_comments = session.run(
            "MATCH (c:Comment) RETURN count(c) AS c"
        ).single()["c"]

    return {
        "mongo_total_threads": total_threads,
        "mongo_unique_threads": unique_threads,
        "mongo_duplicates": duplicates,
        "neo4j_threads": neo_threads,
        "neo4j_comments": neo_comments
    }