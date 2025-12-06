from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from auth.routes import router as auth_router
from auth.utils import verify_token
from chat.routes import router as chat_router
from retrieval.retriever import answer_query

app = FastAPI(title="Smart Research Backend", version="1.0")

# ----------------------
# CORS
# ----------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------
# JWT Dependency
# ----------------------
def require_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "Missing Authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid token format")
    token = authorization.split(" ")[1]
    try:
        return verify_token(token)
    except Exception:
        raise HTTPException(401, "Invalid or expired token")

# ----------------------
# Routers
# ----------------------
app.include_router(auth_router)
app.include_router(chat_router)

# ----------------------
# Request Models
# ----------------------
class AnswerRequest(BaseModel):
    query: str
    mode: str = "simple"
    domain: str = "all"

# ----------------------
# Endpoints
# ----------------------
@app.post("/answer")
def answer(req: AnswerRequest, user=Depends(require_token)):
    return answer_query({
        "query": req.query,
        "mode": req.mode,
        "domain": req.domain
    })

@app.get("/")
def home():
    return {"status": "Smart Research Backend Running!"}

@app.get("/health")
def health():
    return {"status": "API is running"}
