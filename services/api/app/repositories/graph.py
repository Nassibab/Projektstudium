from app.db.neo4j import get_driver


def save_thread_with_comments(thread: dict, comments: list[dict]):
    driver = get_driver()

    with driver.session() as session:
        session.execute_write(_save_thread_with_comments_batch, thread, comments)


def _save_thread_with_comments_batch(tx, thread: dict, comments: list[dict]):
    tx.run(
        """
        MERGE (t:Thread {id: $thread_id})
        SET t.title = $title,
            t.scenario_type = $scenario_type,
            t.label_shitstorm = $label_shitstorm,
            t.description = $description
        """,
        thread_id=thread["thread_id"],
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

        MERGE (c:Comment {id: toString(msg._id)})
        SET c.message_id = msg.message_id,
            c.text = msg.text,
            c.subject = msg.subject,
            c.created = msg.created,
            c.toxicity_level = msg.toxicity_level,
            c.synthetic = msg.synthetic,
            c.synthetic_role = msg.synthetic_role

        MERGE (t:Thread {id: $thread_id})

        MERGE (u)-[:WROTE]->(c)
        MERGE (c)-[:IN_THREAD]->(t)
        """,
        thread_id=thread["thread_id"],
        comments=comments,
    )

    tx.run(
        """
        UNWIND $comments AS msg
        WITH msg
        WHERE msg._id IS NOT NULL
          AND msg.parent IS NOT NULL

        MATCH (c:Comment {id: toString(msg._id)})
        MATCH (parent:Comment {message_id: msg.parent})
        MERGE (c)-[:REPLY_TO]->(parent)
        """,
        comments=comments,
    )

    tx.run(
        """
        UNWIND $comments AS msg
        WITH msg
        WHERE msg.target_login IS NOT NULL

        MERGE (u:User {login: coalesce(msg.login, "unknown")})
        MERGE (target:User {login: msg.target_login})
        MERGE (u)-[:REPLIED_TO_USER]->(target)
        """,
        comments=comments,
    )