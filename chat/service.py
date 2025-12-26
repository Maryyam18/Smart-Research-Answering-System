
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

def isChatExists(session_id:str,user_id:str):
    supabase = get_client()
    result = (
        supabase.table("chat_messages")
        .select("id")
        .eq("session_id", session_id)
        .execute()
    )

    return len(result.data) > 0


def getChatTitle(query:str):
     # Take first sentence or 60 chars
    title = query.strip()
    if '?' in title:
        title = title.split('?')[0] + '?'
    elif '.' in title:
        title = title.split('.')[0]
    
    return title[:60] + "..." if len(title) > 60 else title
    


def save_message(session_id: int, question: str, content: str, user_id: str,corrected_query:str,references:str):
    supabase = get_client()
    if not isChatExists(session_id, user_id):
        title = getChatTitle(corrected_query if corrected_query else question)
        supabase.table("chat_sessions").update({
        "title": title
        }).eq("id", session_id).eq("user_id", user_id).execute()
  
   
    supabase.table("chat_messages").insert({
        "session_id": session_id,
        "question": question,
        "content": content,
        "corrected_query": corrected_query,
        "references": references
    }).execute()


def get_history_title_service(user_id: str):

    supabase = get_client()

    result = (
        supabase.table("chat_sessions")
        .select("id, title, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    if not result.data:
        return []

    return [
        {"session_id": row["id"], "title": row["title"], "created_at": row["created_at"]}
        for row in result.data
    ]
    
def get_chat_history(session_id: int, limit: int = 50):
    supabase = get_client()

    result = (
        supabase.table("chat_messages")
        .select("question, content, created_at,corrected_query,references")
        .eq("session_id", session_id)
        .order("created_at")
        .limit(limit)
        .execute()
    )

    return [(row["question"], row["content"], row["created_at"],row["corrected_query"], row["references"]) for row in result.data]


async def process_user_message(session_id: int, user_msg: str, user_id:str,mode: str = "simple",):
    """
    Process a user message with optional mode:
    mode="simple" (default) or mode="deep"
    """

    # Load chat history
    history = get_chat_history(session_id)

    # Build prompt for RAG / LLM
    context = ""
    for question, answer, created_at, corrected_query, references in history:
        user_question = corrected_query if corrected_query else question
        context += f"USER: {user_question}\n"
        context += f"ASSISTANT: {answer}\n"


    # Get answer from RAG with mode
    result = await answer_query({"context": context, "Actualquery":user_msg, "mode": mode})
    answer = result["answer"]
    references = result.get("references", "")
    corrected_query = result.get("corrected_query", "")
    
    # Save assistant message
    save_message(session_id, user_msg, answer,user_id, corrected_query, references)

    return result
