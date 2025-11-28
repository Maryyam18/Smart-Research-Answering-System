import psycopg2
from sentence_transformers import SentenceTransformer
from fastapi import FastAPI
from pydantic import BaseModel
from pgvector.psycopg2 import register_vector
from groq import Groq
from dotenv import load_dotenv
import os
import re
import requests
import json
import os
import json
load_dotenv()

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
print(f"[DEBUG] GEMINI_API_KEY loaded: {GEMINI_API_KEY[:20] + '...' if GEMINI_API_KEY else 'NOT FOUND'}")

def gemini_autocorrect(query: str) -> str:
    """
    Sends a prompt to Gemini to autocorrect spelling, grammar, and informal words.
    Returns the corrected query.
    """
    if not GEMINI_API_KEY:
        print("[ERROR] GEMINI_API_KEY is not set in .env file!")
        return query

    prompt = f"Correct spelling and grammar: '{query}' Return ONLY the corrected text."

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 100
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

    try:
        print(f"\n[Gemini] Attempting correction for: '{query}'")
        print(f"[Gemini] URL: {url[:80]}...")
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        print(f"[Gemini] Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            corrected = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"[Gemini] âœ… SUCCESS - Corrected: '{corrected}'")
            return corrected
        else:
            error_msg = response.json().get("error", {}).get("message", response.text)
            print(f"[Gemini] âŒ ERROR ({response.status_code}): {error_msg}")
            return query

    except Exception as e:
        print(f"[Gemini] âŒ Exception: {type(e).__name__}: {str(e)}")
        return query
# === CONFIG ===
DB_CONFIG = {
    "host": "localhost", "port": 5432, "user": "postgres",
    "password": "hello098", "dbname": "smart_research"
}
EMBED_MODEL = "all-MiniLM-L6-v2"
TOP_K = 1
SIMILARITY_THRESHOLD = 0.40
GREETING_KEYWORDS = ["hi", "hello", "aoa", "assalam", "how r u", "hey", "salaam", "how are you"]
PERSONAL_KEYWORDS = ["my name", "your name", "friend name", "who am i", "who are you"]

# === GROQ API SETUP ===
GROQ_API_KEY = "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"
groq_client = Groq(api_key=GROQ_API_KEY)

# === MODELS ===
print("Loading embedding model...")
retrieval_model = SentenceTransformer(EMBED_MODEL)
print("Loaded.")
print("Using Groq API (Llama 3) - Fast & Free!")
print("Ready in 2 seconds!")

# === QUERY CLASSIFIER ===
CLASSIFY_PROMPT = """Classify the query into ONE category:
- GREETING: Simple greetings like 'hi', 'hello', 'salaam', 'how are you' (no substantive content).
- VAGUE: Incomplete, unclear, or too short (e.g., 'Wha?', single words like 'what', punctuation-only).
- OUT_OF_DOMAIN: Unrelated to NLP (e.g., cars, physics, biology, economics, personal questions like 'my name').
- IN_DOMAIN: Related to NLP, language models, text processing, embeddings, or AI language tasks.
Return only the category name in uppercase. Be precise: queries about NLP, bias, models, or text analysis are IN_DOMAIN. Personal questions are OUT_OF_DOMAIN.
Query: {query}
Category:"""

def classify_query(query: str) -> str:
    query_lower = query.lower().strip()
    # Fallback: keyword-based check for greetings
    if any(g in query_lower for g in GREETING_KEYWORDS) and len(query_lower.split()) <= 2:
        print("Keyword-based: Classified as GREETING")
        return "GREETING"

    # Check for personal or irrelevant questions
    if any(p in query_lower for p in PERSONAL_KEYWORDS):
        print("Keyword-based: Classified as OUT_OF_DOMAIN (personal question)")
        return "OUT_OF_DOMAIN"

    # Vague check for short or unclear queries
    if len(query_lower.split()) <= 1 or re.match(r"^[^\w\s]+$", query_lower):
        print("Keyword-based: Classified as VAGUE (too short or unclear)")
        return "VAGUE"

    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": CLASSIFY_PROMPT.format(query=query)}],
            max_tokens=10,
            temperature=0.0,
        )
        classification = resp.choices[0].message.content.strip().upper()
        print(f"Classifier output: {classification}")
        # Ensure NLP-related queries are correctly classified
        if any(term in query_lower for term in ["nlp", "language model", "embedding", "text", "bias", "bert", "gpt"]):
            classification = "IN_DOMAIN"
            print("Overridden to IN_DOMAIN due to NLP keywords")
        return classification
    except Exception as e:
        print(f"Classifier Error: {e}")
        return "IN_DOMAIN"  # Safe fallback to check DB

def get_paper_context(query: str):
    try:
        print(f"Query: '{query}'")
        conn = psycopg2.connect(**DB_CONFIG)
        register_vector(conn)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM papers WHERE embedding IS NOT NULL;")
        count = cur.fetchone()[0]
        print(f"Papers with embeddings: {count}")

        q_emb = retrieval_model.encode(query, normalize_embeddings=True)

        cur.execute("""
            SELECT title, authors, year, section_heading, section_text,
                   1 - (embedding <=> %s) AS sim
            FROM papers
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s
            LIMIT %s;
        """, (q_emb, q_emb, TOP_K))

        row = cur.fetchone()
        if row:
            print(f"Found match! Similarity: {row[5]:.3f}")
            print(f"Paper: {row[0]}")
        else:
            print("No match found")

        cur.close()
        conn.close()

        if not row or row[5] < SIMILARITY_THRESHOLD:
            print(f"Threshold failed: {row[5] if row else 'N/A'} < {SIMILARITY_THRESHOLD}")
            return None, None, None

        text = row[4].strip()
        if len(text) > 380:
            text = text[:377] + "..."

        context = f"From section '{row[3]}': {text}"
        authors = ", ".join(row[1][:3])
        ref = f"{row[0]} by {authors}, {row[2]}"
        print(f"Context ready: {context[:100]}...")
        return context, ref, None

    except Exception as e:
        print(f"DB Error: {e}")
        return None, None, "Database error. Please try again!"

# === ANSWER GENERATION ===
ANSWER_PROMPT = """Answer in 3-4 short, simple sentences for a high school student.
Use ONLY the provided context if available and not 'None'.
If context is 'None', use general NLP knowledge and end with: "This is general NLP knowledge â€“ not found in our research papers."
Always end with: Reference: {ref}
Query: {query}
Context: {context}
Answer:"""

def generate_answer(query: str, context: str | None, ref: str | None):
    cls = classify_query(query)
    print(f"Classification: {cls}")

    # 1. GREETING
    if cls == "GREETING":
        print("Responding as greeting")
        return "Hello! I'm ready to answer your questions about NLP research. What would you like to know?", "No paper"

    # 2. VAGUE
    if cls == "VAGUE":
        print("Responding as vague")
        return "Your query is too vague. Please provide more details about the NLP topic!", "No paper"

    # 3. OUT_OF_DOMAIN
    if cls == "OUT_OF_DOMAIN":
        print("Responding as out-of-domain")
        return "Sorry, I can only answer questions about NLP research. Try asking about language models or text processing!", "No paper"

    # 4 & 5. IN_DOMAIN (check DB)
    context, ref, error = get_paper_context(query)
    if error:
        print("Responding with DB error")
        return f"Sorry, there was an error: {error}", "No paper"

    # DB hit with good similarity
    if context and ref:
        print("Using DB context")
        prompt = ANSWER_PROMPT.format(query=query, context=context, ref=ref)
        ref_to_use = ref
    else:
        # 4. IN_DOMAIN but not in DB or 5. Unclear in DB
        print("Using general NLP knowledge (no DB match)")
        prompt = ANSWER_PROMPT.format(query=query, context="None", ref="General NLP knowledge")
        ref_to_use = "General NLP knowledge"

    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=180,
            temperature=0.3,
        )
        answer = resp.choices[0].message.content.strip()
        # Clean any incorrect references and ensure correct one
        if not answer.endswith(f"Reference: {ref_to_use}"):
            answer = answer.split("Reference:")[0].strip() + f"\n\nReference: {ref_to_use}"
        print(f"Answer generated: {answer[:100]}...")
        return answer, ref_to_use

    except Exception as e:
        print(f"Groq Error: {e}")
        return "Sorry, the AI is busy. Try again!", "No paper"

# === FASTAPI ===
app = FastAPI(title="Smart Research MVP")
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Query(BaseModel):
    query: str
@app.post("/answer")
async def answer(q: Query):
    original_query = q.query.strip().lower()

    # Fast keyword check for pure greetings (before wasting Gemini call)
    if any(greeting in original_query for greeting in GREETING_KEYWORDS) and len(original_query.split()) <= 3:
        return {
            "original_query": q.query,
            "corrected_query": q.query,        # don't change it
            "answer": "Hello! I'm your NLP research assistant. Ask me anything about language models, embeddings, BERT, Transformers, etc.! ",
            "source": "Greeting"
        }

    corrected_query = gemini_autocorrect(q.query)
    if corrected_query != q.query:
        print(f"[Gemini] Autocorrected: '{q.query}' → '{corrected_query}'")

    ans_text, source = generate_answer(corrected_query, None, None)

    return {
        "original_query": q.query,
        "corrected_query": corrected_query,
        "answer": ans_text,
        "source": source
    }

@app.get("/health")
async def health():
    return {"status": "MVP ready with Groq API"}


class DebugQuery(BaseModel):
    query: str


@app.post("/debug_gemini")
async def debug_gemini(q: DebugQuery):
    """Call Gemini with the same payload used by autocorrect and return raw JSON plus extracted text.

    This lets you inspect exactly what Gemini returned without reading server logs.
    """
    if not GEMINI_API_URL or not GEMINI_API_KEY:
        return {"error": "GEMINI_API_URL or GEMINI_API_KEY not set in environment"}

    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
    prompt = (
        "You are a spelling and grammar correction assistant. "
        "Correct ONLY the spelling and grammar of the following user query. "
        "Return ONLY the corrected query, with no explanations, no extra text, and no formatting. "
        f"User query: {q.query}"
    )
    payload = {
        "temperature": 0,
        "maxOutputTokens": 64,
        "candidate_count": 1,
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ]
    }
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"error": f"HTTP error calling Gemini: {e}"}

    corrected = None
    candidates = data.get("candidates") or []
    if candidates:
        try:
            corrected = candidates[0].get("content", {}).get("parts", [])[0].get("text", "").strip()
        except Exception:
            corrected = None

    if not corrected and "output_text" in data:
        corrected = data.get("output_text", "").strip()
    if not corrected and "choices" in data and data["choices"]:
        corrected = data["choices"][0].get("text", "").strip()

    return {"raw": data, "extracted_corrected": (corrected or "")}