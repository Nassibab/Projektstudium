from app.db.neo4j import get_driver


def save_thread(tx, thread: dict):
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


def save_comment(tx, msg: dict):
    tx.run(
        """
        MERGE (u:User {login: $login})

        MERGE (c:Comment {id: $message_id})
        SET c.text = $text,
            c.subject = $subject,
            c.created = $created,
            c.toxicity_level = $toxicity_level,
            c.synthetic = $synthetic,
            c.synthetic_role = $synthetic_role

        MERGE (t:Thread {id: $thread_id})

        MERGE (u)-[:WROTE]->(c)
        MERGE (c)-[:IN_THREAD]->(t)
        """,
        login=msg["login"],
        message_id=msg["message_id"],
        thread_id=msg["thread_id"],
        text=msg.get("text"),
        subject=msg.get("subject"),
        created=msg.get("created"),
        toxicity_level=msg.get("toxicity_level"),
        synthetic=msg.get("synthetic"),
        synthetic_role=msg.get("synthetic_role"),
    )


def save_reply_relation(tx, msg: dict):
    parent = msg.get("parent")

    if parent is None:
        return

    tx.run(
        """
        MATCH (c:Comment {id: $message_id})
        MERGE (parent:Comment {id: $parent_id})
        MERGE (c)-[:REPLY_TO]->(parent)
        """,
        message_id=msg["message_id"],
        parent_id=parent,
    )


def save_target_user_relation(tx, msg: dict):
    target_login = msg.get("target_login")

    if not target_login:
        return

    tx.run(
        """
        MERGE (u:User {login: $login})
        MERGE (target:User {login: $target_login})
        MERGE (u)-[:REPLIED_TO_USER]->(target)
        """,
        login=msg["login"],
        target_login=target_login,
    )


def save_thread_with_comments(thread: dict, comments: list[dict]):
    driver = get_driver()

    with driver.session() as session:
        session.execute_write(save_thread, thread)

        for msg in comments:
            session.execute_write(save_comment, msg)
            session.execute_write(save_reply_relation, msg)
            session.execute_write(save_target_user_relation, msg)