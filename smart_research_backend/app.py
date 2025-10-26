import psycopg2
from sentence_transformers import SentenceTransformer
from fastapi import FastAPI
from pydantic import BaseModel
from pgvector.psycopg2 import register_vector
from transformers import pipeline

# === CONFIG ===
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "user": "postgres",
    "password": "hello098",
    "dbname": "smart_research"
}

EMBED_MODEL = "all-MiniLM-L6-v2"
TOP_K = 5
SIMILARITY_THRESHOLD = 0.7

# === LOAD EMBEDDING MODEL ===
print("🔹 Loading embedding model...")
retrieval_model = SentenceTransformer(EMBED_MODEL)
print("✅ Embedding model loaded successfully.")

# === LOAD LOCAL ANSWER GENERATION MODEL (Hugging Face) ===
print("🔹 Loading local LLM summarization model...")
summarizer = pipeline("text2text-generation", model="google/flan-t5-small")
print("✅ Local summarization model loaded.")

# === RETRIEVAL FUNCTION ===
def retrieve_contexts(query: str):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        register_vector(conn)
        cur = conn.cursor()

        query_emb = retrieval_model.encode(query, normalize_embeddings=True)

        cur.execute("""
            SELECT paperid, title, authors, year, section_heading, section_text,
                   embedding <=> %s AS distance
            FROM papers
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s
            LIMIT %s;
        """, (query_emb, query_emb, TOP_K))

        results = cur.fetchall()
        cur.close()
        conn.close()

        if not results:
            return None, None

        best_distance = results[0][6]
        if best_distance > SIMILARITY_THRESHOLD:
            return None, None

        contexts = []
        for row in results:
            context_text = f"Section '{row[4]}': {row[5][:400]}..."
            contexts.append(context_text)

        best_paper_info = f"{results[0][1]} by {results[0][2]}, {results[0][3]}"
        combined_context = "\n\n".join(contexts)
        return combined_context, best_paper_info

    except Exception as e:
        print(f"❌ Error in retrieve_contexts: {e}")
        return None, None

# === LOCAL ANSWER GENERATION FUNCTION ===
def generate_answer(query, contexts, best_paper):
    if contexts is None:
        # No relevant paper found
        return "Sorry, no relevant research found in your database.", None

    prompt = f"Answer the question in 3-4 concise lines using ONLY the research context below. Include the reference at the end.\n\nQuestion: {query}\n\nContext:\n{contexts}\n\nReference: {best_paper}"

    result = summarizer(prompt, max_length=200, do_sample=False)
    answer = result[0]['generated_text']
    return answer, best_paper

# === FASTAPI APP ===
app = FastAPI(title="Smart Research Answering System", version="1.0.0")

class Query(BaseModel):
    query: str

@app.post("/answer")
async def answer(q: Query):
    print(f"🌐 Received query: {q.query}")

    contexts, best_paper = retrieve_contexts(q.query)
    answer_text, reference = generate_answer(q.query, contexts, best_paper)

    return {
        "query": q.query,
        "answer": answer_text,
        "source": reference if reference else "No relevant research found"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Smart Research API is running"}

# === RUN THE APP ===
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Smart Research Answering System...")
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)