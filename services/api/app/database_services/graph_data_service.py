from app.db.neo4j import get_driver


def save_thread_with_comments(thread: dict, comments: list[dict]):
    driver = get_driver()

    with driver.session() as session:
        session.execute_write(_save_thread_with_comments_batch, thread, comments)


def _save_thread_with_comments_batch(tx, thread: dict, comments: list[dict]):
    source_platform = thread.get("source_platform", "unknown")
    source_type = thread.get("source_type", "unknown")

    original_thread_id = thread["thread_id"]

    # Für Neo4j eindeutige Thread-ID bauen
    graph_thread_id = f"{source_platform}:{source_type}:{original_thread_id}"

    tx.run(
        """
        MERGE (d:Dataset {id: $dataset_id})
        SET d.source_platform = $source_platform,
            d.source_type = $source_type

        MERGE (t:Thread {id: $graph_thread_id})
        SET t.original_thread_id = $original_thread_id,
            t.source_platform = $source_platform,
            t.source_type = $source_type,
            t.title = $title,
            t.comments_count = $comments_count,
            t.scenario_type = $scenario_type,
            t.label_shitstorm = $label_shitstorm,
            t.description = $description,
            t.source_file = $source_file

        MERGE (d)-[:CONTAINS_THREAD]->(t)
        """,
        dataset_id=f"{source_platform}:{source_type}",
        source_platform=source_platform,
        source_type=source_type,
        graph_thread_id=graph_thread_id,
        original_thread_id=original_thread_id,
        title=thread.get("title"),
        comments_count=thread.get("comments_count", 0),
        scenario_type=thread.get("scenario_type"),
        label_shitstorm=thread.get("label_shitstorm"),
        description=thread.get("description"),
        source_file=thread.get("source_file"),
    )

    tx.run(
        """
        UNWIND $comments AS msg
        WITH msg
        WHERE msg.comment_id IS NOT NULL

        MERGE (u:User {user: coalesce(msg.user, "unknown")})

        MERGE (c:Comment {
            id: $graph_thread_id + ":" + toString(msg.comment_id)
        })
        SET c.original_id = toString(msg.comment_id),
            c.thread_id = msg.thread_id,
            c.source_platform = msg.source_platform,
            c.source_type = msg.source_type,
            c.comment_id = msg.comment_id,
            c.text = msg.text,
            c.created_at = msg.created_at,
            c.subject = msg.subject,
            c.toxicity_level = msg.toxicity_level,
            c.synthetic = msg.synthetic,
            c.synthetic_role = msg.synthetic_role,
            c.target_user = msg.target_user

        WITH c, u
        MATCH (t:Thread {id: $graph_thread_id})

        MERGE (u)-[:WROTE]->(c)
        MERGE (c)-[:IN_THREAD]->(t)
        """,
        graph_thread_id=graph_thread_id,
        comments=comments,
    )

    tx.run(
        """
        UNWIND $comments AS msg
        WITH msg
        WHERE msg.parent_id IS NOT NULL

        MATCH (c:Comment {
            id: $graph_thread_id + ":" + toString(msg.comment_id)
        })

        MATCH (parent:Comment {
            id: $graph_thread_id + ":" + toString(msg.parent_id)
        })

        MERGE (c)-[:REPLY_TO]->(parent)
        """,
        graph_thread_id=graph_thread_id,
        comments=comments,
    )

    tx.run(
        """
        UNWIND $comments AS msg
        WITH msg
        WHERE msg.target_user IS NOT NULL

        MERGE (u:User {user: coalesce(msg.user, "unknown")})
        MERGE (target:User {user: msg.target_user})

        MERGE (u)-[:REPLIED_TO_USER {
            thread_id: $graph_thread_id,
            source_platform: msg.source_platform,
            source_type: msg.source_type
        }]->(target)
        """,
        graph_thread_id=graph_thread_id,
        comments=comments,
    )