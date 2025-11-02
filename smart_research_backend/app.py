# app_mvP.py – CLEAN, USER-FRIENDLY, 3-4 LINES + 1 REFERENCE
import psycopg2
from sentence_transformers import SentenceTransformer
from fastapi import FastAPI
from pydantic import BaseModel
from pgvector.psycopg2 import register_vector
from groq import Groq
from dotenv import load_dotenv
import os
import re

# === CONFIG ===
DB_CONFIG = {
    "host": "localhost", "port": 5432, "user": "postgres",
    "password": "hello098", "dbname": "smart_research"
}
EMBED_MODEL = "all-MiniLM-L6-v2"  # Reverted to match your database embeddings
TOP_K = 1
SIMILARITY_THRESHOLD = 0.40  # Fixed for your data
GREETING_KEYWORDS = ["hi", "hello", "aoa", "assalam", "how r u", "hey", "salaam", "how are you"]

# === GROQ API SETUP ===
GROQ_API_KEY = "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"  # Your Groq key
groq_client = Groq(api_key=GROQ_API_KEY)

# === MODELS ===
print("Loading embedding model...")
retrieval_model = SentenceTransformer(EMBED_MODEL)
print("Loaded.")
print("Using Groq API (Llama 3) - Fast & Free!")
print("Ready in 2 seconds!")

# === QUERY VALIDATION ===
def is_valid_query(query: str) -> tuple[bool, str]:
    query = query.strip().lower()
    # Check for greetings
    if any(greeting in query for greeting in GREETING_KEYWORDS):
        return False, "Hello! I'm ready to answer your questions about NLP research. What would you like to know?"
    # Check for vague or incomplete queries
    if len(query) < 3 or re.match(r"^[^\w\s]+$", query) or query in ["wh", "what", "?", ""]:
        return False, "Your query seems unclear. Could you provide more details about what you're asking?"
    # Check for single-word queries
    if len(query.split()) == 1:
        return False, f"Could you clarify what you mean by '{query}'? Are you asking about an NLP topic like language models?"
    return True, ""

# === RETRIEVAL: Get BEST matching section ===
def get_paper_context(query: str):
    try:
        print(f"Query: '{query}'")  # Debug

        # Validate query
        is_valid, error_message = is_valid_query(query)
        if not is_valid:
            print(f"Invalid query: {error_message}")
            return None, None, error_message

        conn = psycopg2.connect(**DB_CONFIG)
        register_vector(conn)
        cur = conn.cursor()

        # Count papers
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
            return None, None, "Sorry, I can only answer questions about NLP research. Try asking about language models or text processing!"

        # Clean context
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
        return None, None, "Sorry, there was a database error. Please try again!"

# === ANSWER: Use Groq (Llama 3) to rephrase ===
def generate_answer(query: str, context: str, ref: str, error_message: str):
    if error_message:
        return error_message, "No paper"

    if not context:
        return "Sorry, I can only answer questions about NLP research. Try asking about language models or text processing!", "No paper"

    prompt = f"""
Answer in 3-4 short, simple sentences for a high school student.
Use ONLY the context below to answer the question.
If the context doesn’t have enough information, say: "I couldn’t find a clear answer about this in our NLP research."
End with: Reference: {ref}

Question: {query}
Context: {context}

Answer:
"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3
        )
        answer = response.choices[0].message.content.strip()

        # Ensure reference is at the end
        if ref not in answer:
            answer += f"\n\nReference: {ref}"

        return answer, ref

    except Exception as e:
        print(f"Groq Error: {e}")
        return "Sorry, the AI is busy. Try again!", "No paper"

# === FASTAPI ===
app = FastAPI(title="Smart Research MVP")

class Query(BaseModel):
    query: str

@app.post("/answer")
async def answer(q: Query):
    context, ref, error_message = get_paper_context(q.query)
    answer_text, source = generate_answer(q.query, context, ref, error_message)
    return {
        "query": q.query,
        "answer": answer_text,
        "source": source
    }

@app.get("/health")
async def health():
    return {"status": "MVP ready with Groq API"}