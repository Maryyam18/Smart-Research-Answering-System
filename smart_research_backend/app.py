# 

# app.py
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from auth.routes import router as auth_router
from auth.utils import verify_token
from chat.routes import router as chat_router
from retrieval.retriever import answer_query

# import supabase client
from supabase_client import supabase

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
# Startup check (optional but useful)
# ----------------------
@app.on_event("startup")
def startup_check():
    try:
        # quick lightweight query to confirm keys/connection
        resp = supabase.table("users").select("id").limit(1).execute()
        # supabase client returns dict-like object with `data` and `error`
        if getattr(resp, "error", None):
            # raise to log on startup
            raise RuntimeError(f"Supabase startup check error: {resp.error}")
    except Exception as e:
        # if you prefer not to crash on bad env, comment out raise
        raise RuntimeError(f"Failed to reach Supabase at startup: {e}")

# ----------------------
# JWT Dependency
# ----------------------
def require_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    token = authorization.split(" ", 1)[1]

    # verify_token should decode JWT and return payload (e.g. {'sub': 'user-id', ...})
    try:
        payload = verify_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing user id")

    # fetch user from Supabase users table (adjust column/table name to your schema)
    resp = supabase.table("users").select("*").eq("id", user_id).single().execute()
    if getattr(resp, "error", None) or resp.data is None:
        raise HTTPException(status_code=401, detail="User not found or DB error")

    # return the user record to route handlers as `user`
    return resp.data

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
    # user is the row from Supabase users table
    return answer_query({
        "query": req.query,
        "mode": req.mode,
        "domain": req.domain,
        "user": user,   # optional: pass user info to your retriever if needed
    })

@app.get("/")
def home():
    return {"status": "Smart Research Backend Running!"}

@app.get("/health")
def health():
    # you can do a tiny supabase quick check here too if you want
    return {"status": "API is running"}
