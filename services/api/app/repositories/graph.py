from app.db.neo4j import get_driver


def save_thread_with_comments(thread: dict, comments: list[dict]):
    driver = get_driver()

    with driver.session() as session:
        session.execute_write(_save_thread_with_comments_batch, thread, comments)


def _save_thread_with_comments_batch(tx, thread: dict, comments: list[dict]):
    source_file = thread.get("source_file", "unknown_source")
    original_thread_id = thread["thread_id"]
    graph_thread_id = f"{source_file}:{original_thread_id}"

    tx.run(
        """
        MERGE (d:Dataset {id: $source_file})
        SET d.source_file = $source_file

        MERGE (t:Thread {id: $graph_thread_id})
        SET t.original_thread_id = $original_thread_id,
            t.source_file = $source_file,
            t.title = $title,
            t.scenario_type = $scenario_type,
            t.label_shitstorm = $label_shitstorm,
            t.description = $description

        MERGE (d)-[:CONTAINS_THREAD]->(t)
        """,
        source_file=source_file,
        graph_thread_id=graph_thread_id,
        original_thread_id=original_thread_id,
        title=thread.get("title"),
        scenario_type=thread.get("scenario_type"),
        label_shitstorm=thread.get("label_shitstorm"),
        description=thread.get("description"),
    )

    tx.run(
        """
        UNWIND $comments AS msg
        WITH msg
        WHERE msg._id IS NOT NULL

        MERGE (u:User {login: coalesce(msg.login, "unknown")})

        MERGE (c:Comment {id: $source_file + ":" + toString(msg._id)})
        SET c.original_id = toString(msg._id),
            c.source_file = $source_file,
            c.message_id = msg.message_id,
            c.text = msg.text,
            c.subject = msg.subject,
            c.created = msg.created,
            c.toxicity_level = msg.toxicity_level,
            c.synthetic = msg.synthetic,
            c.synthetic_role = msg.synthetic_role

        WITH c, u
        MATCH (t:Thread {id: $graph_thread_id})

        MERGE (u)-[:WROTE]->(c)
        MERGE (c)-[:IN_THREAD]->(t)
        """,
        source_file=source_file,
        graph_thread_id=graph_thread_id,
        comments=comments,
    )

    tx.run(
        """
        UNWIND $comments AS msg
        WITH msg
        WHERE msg._id IS NOT NULL
          AND msg.parent IS NOT NULL

        MATCH (c:Comment {id: $source_file + ":" + toString(msg._id)})
        MATCH (parent:Comment {
            message_id: msg.parent,
            source_file: $source_file
        })

        MERGE (c)-[:REPLY_TO]->(parent)
        """,
        source_file=source_file,
        comments=comments,
    )

    tx.run(
        """
        UNWIND $comments AS msg
        WITH msg
        WHERE msg.target_login IS NOT NULL

        MERGE (u:User {login: coalesce(msg.login, "unknown")})
        MERGE (target:User {login: msg.target_login})

        MERGE (u)-[:REPLIED_TO_USER {
            source_file: $source_file,
            thread_id: $graph_thread_id
        }]->(target)
        """,
        source_file=source_file,
        graph_thread_id=graph_thread_id,
        comments=comments,
    )