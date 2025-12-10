from fastapi import APIRouter, Depends, HTTPException, Header
from auth.utils import verify_token
from chat.service import create_new_session, process_user_message, get_chat_history

router = APIRouter(prefix="/chat", tags=["Chat"])

# Dependency to get current user from JWT in Authorization header
def get_current_user(authorization: str = Header(...)):
    """
    Reads Authorization header in the format: "Bearer <token>"
    Returns token payload if valid
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid token format")
    
    token = authorization.split(" ")[1]
    try:
        payload = verify_token(token)
        return payload  # contains uid and sub (email)
    except:
        raise HTTPException(401, "Invalid or expired token")


@router.post("/new")
def new_chat(user=Depends(get_current_user)):
    session_id = create_new_session(user["uid"])
    return {"session_id": session_id}


@router.post("/message")
def send_message(data: dict, user=Depends(get_current_user)):
    if "session_id" not in data or "message" not in data:
        raise HTTPException(400, "session_id and message required")

    session_id = data["session_id"]
    user_msg = data["message"]
    mode = data.get("mode", "simple")  # Default to simple

    answer = process_user_message(session_id, user_msg, mode)
    return {"answer": answer}


@router.get("/history/{session_id}")
def history(session_id: int, user=Depends(get_current_user)):
    msgs = get_chat_history(session_id)
    return [
        {"sender": m[0], "content": m[1], "time": m[2]}
        for m in msgs
    ]
