# app.py 

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
from groq import Groq

app = FastAPI()

# ==========================
# LOAD MODELS AT STARTUP
# ==========================
print("Loading BAAI/bge-small-en-v1.5... (startup may take ~1-2 min)")
model = SentenceTransformer("BAAI/bge-small-en-v1.5")
client = Groq(api_key="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")

# ==========================
# CONFIG
# ==========================
DOMAINS = {
    "NLP",
    "Quantum Information Retrieval and Information Teleportation",
    "Quantum Resistant Cryptography and Identity Based Encryption",
    "VLSI in Power Electronics and Embedded Systems"
}

DB = {"host": "localhost", "port": 5432, "user": "postgres", "password": "hello098", "dbname": "smart_research"}
TOP_K = 20
MIN_SIM = 0.64

class QueryRequest(BaseModel):
    query: str
    mode: str = "simple"
    domain: str = "all"

def get_conn():
    conn = psycopg2.connect(**DB)
    register_vector(conn)
    return conn

# ==========================
# RETRIEVE FUNCTION
# ==========================
def retrieve(q: str, domain: str = "all"):
    conn = get_conn()
    cur = conn.cursor()
    q_emb = model.encode(q, normalize_embeddings=True)

    sql = "SELECT title, authors, year, enriched_text, paperid, embedding <=> %s FROM papers WHERE embedding IS NOT NULL"
    params = [q_emb]

    if domain != "all":
        if domain not in DOMAINS:
            cur.close(); conn.close()
            return None
        sql += " AND domain = %s"
        params.append(domain)

    sql += " ORDER BY embedding <=> %s LIMIT %s"
    cur.execute(sql, params + [q_emb, TOP_K])
    results = cur.fetchall()
    cur.close(); conn.close()

    seen = set()
    good = []
    for row in results:
        dist = row[5]
        if 1 - dist >= MIN_SIM and row[4] not in seen:
            seen.add(row[4])
            good.append(row)
    return good if good else None

def make_ref(title, authors, year):
    a = authors[0] + (" et al." if len(authors) > 1 else "")
    return f"{title} by {a}, {year}"

# ==========================
# API ENDPOINT
# ==========================
@app.post("/answer")
def answer(req: QueryRequest):
    mode = req.mode.lower()
    if mode not in ["simple", "deep"]:
        raise HTTPException(status_code=400, detail="mode must be 'simple' or 'deep'")

    results = retrieve(req.query, req.domain if req.domain != "all" else "all")

    if not results:
        msg = "Sorry, I couldn't find any relevant research papers on this topic. I only know about NLP, Quantum Computing, Quantum Cryptography, and VLSI."
        return {"answer": msg, "reference" if mode == "simple" else "references": None if mode == "simple" else []}

    # --------------------------
    # SIMPLE MODE
    # --------------------------
    if mode == "simple":
        context = "\n\n".join([r[3] for r in results[:8]])
        best = results[0]

        prompt = f"""Answer in 3-4 short sentences using only these sources.
Do NOT mention titles, authors, or years.

Question: {req.query}
Sources: {context}
Answer:"""

        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=280,
            temperature=0.1
        )
        answer_text = resp.choices[0].message.content.strip()
        answer_text += f"\n\nReference: {make_ref(best[0], best[1], best[2])}"
        return {"answer": answer_text, "reference": make_ref(best[0], best[1], best[2])}

    # --------------------------
    # DEEP MODE (ALWAYS ANSWER)
    # --------------------------
    context = ""
    refs = []
    used = set()
    for row in results:
        pid = row[4]
        if pid in used or len(refs) >= 4: 
            continue
        used.add(pid)
        context += f"{row[3]}\n\n"
        refs.append(make_ref(row[0], row[1], row[2]))

    prompt = f"""You are an expert researcher. Give a detailed answer using only these sources.

Question: {req.query}
Sources:
{context}

Answer in clear paragraphs. End with "References are listed below."
"""
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
        temperature=0.3
    )
    answer_text = resp.choices[0].message.content.strip()

    # ADD SUMMARY / CONCLUSION
    summary_prompt = f"""Summarize the above answer in 3-4 lines, highlighting the main conclusion.
Answer:
{answer_text}
Summary:"""

    summary_resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": summary_prompt}],
        max_tokens=150,
        temperature=0.1
    )
    summary_text = summary_resp.choices[0].message.content.strip()

    answer_text += f"\n\nConclusion:\n{summary_text}\n\nReferences:\n" + "\n".join(f"• {r}" for r in refs)
    return {"answer": answer_text, "references": refs}
