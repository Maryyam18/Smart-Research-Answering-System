
from retrieval.retriever import answer_query
from supabaseclient import get_client

def create_new_session(user_id: int):
    supabase = get_client()

    result = (
        supabase.table("chat_sessions")
        .insert({"user_id": user_id})
        .execute()
    )
    
    if not result.data:
        raise Exception("Failed to create chat session")

    return result.data[0]["id"]


def save_message(session_id: int, sender: str, content: str):
    supabase = get_client()

    supabase.table("chat_messages").insert({
        "session_id": session_id,
        "sender": sender,
        "content": content
    }).execute()


def get_chat_history(session_id: int, limit: int = 50):
    supabase = get_client()

    result = (
        supabase.table("chat_messages")
        .select("sender, content, created_at")
        .eq("session_id", session_id)
        .order("created_at", asc=True)
        .limit(limit)
        .execute()
    )

    return [(row["sender"], row["content"], row["created_at"]) for row in result.data]


async def process_user_message(session_id: int, user_msg: str, mode: str = "simple"):
    """
    Process a user message with optional mode:
    mode="simple" (default) or mode="deep"
    """
    # Save user message
    save_message(session_id, "user", user_msg)

    # Load chat history
    history = get_chat_history(session_id)

    # Build prompt for RAG / LLM
    context = ""
    for sender, content, _ in history:
        context += f"{sender.upper()}: {content}\n"
    prompt = context + f"USER: {user_msg}\nASSISTANT:"

    # Get answer from RAG with mode
    answer = await answer_query({"query": user_msg, "mode": mode})["answer"]

    # Save assistant message
    save_message(session_id, "assistant", answer)

    return answer

async def process_user_message_query( user_msg: str, mode: str = "deep"):
    """
    Process a user message with optional mode:
    mode="simple" (default) or mode="deep"
    """
    # Build prompt for RAG / LLM
    context = ""
    prompt = context + f"USER: {user_msg}\nASSISTANT:"

    # Get answer from RAG with mode
    answer = await answer_query({"query": user_msg, "mode": mode})["answer"]

    return answer
