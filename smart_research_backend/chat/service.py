from database.connection import get_conn
from retrieval.retriever import answer_query

def create_new_session(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO chat_sessions (user_id)
        VALUES (%s)
        RETURNING id
    """, (user_id,))
    session_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return session_id

def save_message(session_id: int, sender: str, content: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO chat_messages (session_id, sender, content)
        VALUES (%s, %s, %s)
    """, (session_id, sender, content))
    conn.commit()
    cur.close()
    conn.close()

def get_chat_history(session_id: int, limit: int = 50):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT sender, content, created_at
        FROM chat_messages
        WHERE session_id=%s
        ORDER BY created_at ASC
        LIMIT %s
    """, (session_id, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def process_user_message(session_id: int, user_msg: str, mode: str = "simple"):
    # Save user message
    save_message(session_id, "user", user_msg)

    # Call retriever with session_id as int
    result = answer_query({
        "query": user_msg,
        "mode": mode,
        "session_id": int(session_id)   # <-- Ye important hai, int mein convert
    })

    answer = result["answer"]

    # Save assistant reply
    save_message(session_id, "assistant", answer)

    return answer