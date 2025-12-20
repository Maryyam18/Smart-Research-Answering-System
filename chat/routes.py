from fastapi import APIRouter, Depends, HTTPException, Header
from auth.utils import verify_token
from chat.service import create_new_session, process_user_message, get_chat_history, process_user_message_query,get_history_title_service

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/new")
def new_chat(userId: str):
    session_id = create_new_session(userId)
    return {"session_id": session_id}


@router.post("/message")
async def send_message(data: dict):
    if "session_id" not in data or "message" not in data:
        raise HTTPException(400, "session_id and message required")

    session_id = data["session_id"]
    user_msg = data["message"]
    mode = data.get("mode", "simple")  # Default to simple
    user_id = data["user_id"] # Default to empty string

    answer = await process_user_message(session_id, user_msg,user_id, mode)
    return {answer}


@router.post("/messageQuery")
async def send_message(data: dict):
    if "message" not in data:
        raise HTTPException(400, "message required")

    
    user_msg = data["message"]
    mode = data.get("mode", "simple")  # Default to simple

    answer = await process_user_message_query( user_msg, mode)
    return {"answer": answer}


@router.get("/history/{session_id}")
def history(session_id: int):
    msgs = get_chat_history(session_id)
    return [
        {"question": m[0], "content": m[1], "time": m[2]}
        for m in msgs
    ]

@router.get("/getHistoryTitle/{user_id}")
def get_history_title(user_id: str):
    titles = get_history_title_service(user_id)
    return {"history": titles}
