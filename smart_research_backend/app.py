from fastapi import FastAPI, Depends, Header, HTTPException
from auth.routes import router as auth_router
from auth.utils import verify_token
from retrieval.retriever import answer_query

app = FastAPI()

app.include_router(auth_router)

def require_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid token format")

    token = authorization.split(" ")[1]

    try:
        return verify_token(token)
    except:
        raise HTTPException(401, "Invalid or expired token")

@app.post("/answer")
def answer(req: dict, user=Depends(require_token)):
    return answer_query(req)
