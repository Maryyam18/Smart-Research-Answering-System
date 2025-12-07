from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from auth.routes import router as auth_router
from chat.routes import router as chat_router
from auth.utils import verify_token
from retrieval.retriever import answer_query

app = FastAPI(title="Smart Research Backend", version="1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Dependency
def require_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "Missing Authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid token format")

    token = authorization.split(" ")[1]
    try:
        payload = verify_token(token)
        return payload  # contains uid + email
    except Exception:
        raise HTTPException(401, "Invalid or expired token")


# Include routers
app.include_router(auth_router)
app.include_router(chat_router)  # Chat system integrated

# RAG endpoint
@app.post("/answer")
def answer(req: dict, user=Depends(require_token)):
    return answer_query(req)

@app.get("/")
def home():
    return {"status": "Smart Research Backend Running!"}
