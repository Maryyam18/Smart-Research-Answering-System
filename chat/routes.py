from fastapi import APIRouter, Depends, HTTPException, Header
from auth.utils import verify_token
from chat.service import create_new_session, process_user_message, get_chat_history,get_history_title_service, delete_chat_session

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/new")
def new_chat(userId: str):
    session_id = create_new_session(userId)
    return {"session_id": session_id}

@router.delete("/delete/{session_id}")
def delete_chat(session_id: str):
    try:
        result = delete_chat_session(session_id)
        if result==True:
            return {"success":"true","message": f"Chat session {session_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/message")
async def send_message(data: dict):
    if "message" not in data:
        raise HTTPException(400, "Query is required")

    session_id = data.get("session_id")
    user_msg = data["message"]
    mode = data.get("mode", "simple")  # Default to simple
    user_id = data["user_id"] # Default to empty string
    ##even if session id is not provided, we can create a new session if user_id is given
    if not session_id:
        if not user_id:
            raise HTTPException(400, "user_id required when creating new session")
        session_id = create_new_session(user_id)
    answer = await process_user_message(session_id, user_msg,user_id, mode)
    return answer

@router.get("/history/{session_id}")
def history(session_id: int):
    msgs = get_chat_history(session_id)
    return [
        {"question": m[0], "content": m[1], "time": m[2], "corrected_query": m[3], "references": m[4]}
        for m in msgs
    ]

@router.get("/getHistoryTitle/{user_id}")
def get_history_title(user_id: str):
    titles = get_history_title_service(user_id)
    return {"history": titles}
