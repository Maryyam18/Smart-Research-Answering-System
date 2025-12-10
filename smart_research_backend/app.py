from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from auth.routes import router as auth_router
from auth.utils import verify_token
from chat.routes import router as chat_router
from retrieval.retriever import answer_query
from database.connection import get_conn

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
    # Removed domain, as it's dynamic now

# ----------------------
# Endpoints
# ----------------------
@app.post("/answer")
def answer(req: AnswerRequest, user=Depends(require_token)):
    return answer_query({
        "query": req.query,
        "mode": req.mode,
        "session_id": None  # For standalone /answer, no session; adjust if needed
    })

@app.get("/")
def home():
    return {"status": "Smart Research Backend Running!"}

@app.get("/health")
def health():
    return {"status": "API is running"}

# ----------------------
# Startup Event: Create dynamic tables
# ----------------------
@app.on_event("startup")
def startup():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dynamic_papers (
            id SERIAL PRIMARY KEY,
            session_id INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE,
            url TEXT NOT NULL,
            title TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(session_id, url)
        );
        CREATE TABLE IF NOT EXISTS dynamic_chunks (
            id SERIAL PRIMARY KEY,
            paper_id INTEGER REFERENCES dynamic_papers(id) ON DELETE CASCADE,
            chunk_text TEXT NOT NULL,
            embedding VECTOR(384),
            chunk_index INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_dynamic_emb ON dynamic_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    """)
    conn.commit()
    cur.close()
    conn.close()