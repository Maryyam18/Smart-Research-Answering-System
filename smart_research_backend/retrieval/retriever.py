from sentence_transformers import SentenceTransformer
from groq import Groq
from database.connection import get_conn
from autocorrect import gemini_autocorrect  # autocorrect module

from config import settings

DOMAINS = {
    "NLP",
    "Quantum Information Retrieval and Information Teleportation",
    "Quantum Resistant Cryptography and Identity Based Encryption",
    "VLSI in Power Electronics and Embedded Systems"
}

TOP_K = 20
MIN_SIM = 0.64

print("Loading model BAAI/bge-small-en-v1.5...")
model = SentenceTransformer("BAAI/bge-small-en-v1.5")

client = Groq(api_key=settings.GROQ_API_KEY)

def make_ref(title, authors, year):
    a = authors[0] + (" et al." if len(authors) > 1 else "")
    return f"{title} by {a}, {year}"

def retrieve(q: str, domain: str = "all"):
    conn = get_conn()
    cur = conn.cursor()
    q_emb = model.encode(q, normalize_embeddings=True)

    sql = """
        SELECT title, authors, year, enriched_text, paperid, embedding <=> %s
        FROM papers WHERE embedding IS NOT NULL
    """
    params = [q_emb]

    if domain != "all":
        sql += " AND domain=%s"
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

def answer_query(req):
    original_query = req["query"]
    mode = req.get("mode", "simple").lower()
    domain = req.get("domain", "all")

    # ===== AUTOCORRECT =====
    corrected_query = gemini_autocorrect(original_query)
    if corrected_query != original_query:
        print(f"[Retriever] Autocorrected: '{original_query}' → '{corrected_query}'")
    query = corrected_query

    results = retrieve(query, domain)

    if not results:
        return {
            "original_query": original_query,
            "corrected_query": corrected_query,
            "answer": "Sorry, I couldn't find relevant papers.",
            "references": [],
            "mode": mode
        }

    # -------- SIMPLE MODE --------
    if mode == "simple":
        context = "\n\n".join([r[3] for r in results[:8]])
        best = results[0]

        prompt = f"""
Answer in 3-4 short sentences using only these sources.
Do NOT mention titles, authors, or years.

Question: {query}
Sources: {context}
Answer:
"""

        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        )

        answer_text = resp.choices[0].message.content.strip()
        # Add the single reference for simple mode
        answer_text += f"\n\nReference: {make_ref(best[0], best[1], best[2])}"

        return {
            "original_query": original_query,
            "corrected_query": corrected_query,
            "answer": answer_text,
            "reference": make_ref(best[0], best[1], best[2]),
            "references": [make_ref(best[0], best[1], best[2])],
            "mode": "simple"
        }

    # -------- DEEP MODE --------
    context = ""
    refs = []
    used = set()

    for row in results:
        pid = row[4]
        if pid in used or len(refs) >= 4:
            continue
        used.add(pid)
        context += row[3] + "\n\n"
        refs.append(make_ref(row[0], row[1], row[2]))

    prompt = f"""
You are an expert researcher.
Give a detailed answer using only these sources.

Question: {query}
Sources:
{context}

Answer in clear paragraphs.
End with "References are listed below."
"""

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200
    )

    answer_text = resp.choices[0].message.content.strip()

    # Summarize
    summary_prompt = f"""
Summarize the above answer in 3-4 lines.
Answer:
{answer_text}
Summary:
"""
    summary_resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": summary_prompt}],
        max_tokens=150
    )

    summary_text = summary_resp.choices[0].message.content.strip()
    answer_text += f"\n\nConclusion:\n{summary_text}"

    # Add references at the end for deep mode
    answer_text += "\n\nReferences:\n" + "\n".join("• " + r for r in refs)

    return {
        "original_query": original_query,
        "corrected_query": corrected_query,
        "answer": answer_text,
        "references": refs,
        "mode": "deep"
    }
