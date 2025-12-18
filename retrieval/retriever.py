from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from groq import Groq
from autocorrect import gemini_autocorrect  # autocorrect module
from supabaseclient import get_client
from config import settings
from dotenv import load_dotenv
load_dotenv()
from langchain_community.tools.tavily_search import TavilySearchResults
import numpy as np

DOMAINS = {
    "NLP",
    "Quantum Information Retrieval and Information Teleportation",
    "Quantum Resistant Cryptography and Identity Based Encryption",
    "VLSI in Power Electronics and Embedded Systems"
}

TOP_K = 20
MIN_SIM = 0.64

print("Loading model BAAI/bge-small-en-v1.5...")
model = GoogleGenerativeAIEmbeddings(model="text-embedding-004")

client = Groq(api_key=settings.GROQ_API_KEY)



async def run_web_search(query: str, k: int = 4) -> str:
    try:
        tavily = TavilySearchResults(k=k)
        results = tavily.run(query)

        if not results:
            return ""

        formatted = "\n\n".join(
            [
                f"Title: {item.get('title')}\nURL: {item.get('url')}\nSnippet: {item.get('content')}"
                for item in results
            ]
        )

        return formatted

    except Exception as e:
        return f"Web search error: {str(e)}"

def make_ref(title, authors, year):
    a = authors[0] + (" et al." if len(authors) > 1 else "")
    return f"{title} by {a}, {year}"

def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors."""
    import json
    
    # Convert to numpy arrays, handling JSON strings if necessary
    if isinstance(vec1, str):
        vec1 = json.loads(vec1)
    if isinstance(vec2, str):
        vec2 = json.loads(vec2)
    
    vec1 = np.array(vec1, dtype=np.float32)
    vec2 = np.array(vec2, dtype=np.float32)
    
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def retrieve(q: str, domain: str = "all"):
    supabase = get_client()

    q_emb = model.embed_query(q)

    query_builder = (
        supabase.table("papers")
        .select("title, authors, year, enriched_text, paperid, embedding")
        .not_.is_("embedding", None)
    )

    if domain != "all":
        query_builder = query_builder.eq("domain", domain)

    # sql += " ORDER BY embedding <=> %s LIMIT %s"
    # cur.execute(sql, params + [q_emb, TOP_K])
    # results = cur.fetchall()
    # cur.close(); conn.close()
    
    response = query_builder.execute()
    rows = response.data

    # Convert rows into same structure as old SQL result:
    results = []
    for r in rows:
        emb = r["embedding"]

        # compute cosine distance manually
        similarity = cosine_similarity(q_emb, emb)
        dist = 1 - similarity

        results.append([
            r["title"],
            r["authors"],
            r["year"],
            r["enriched_text"],
            r["paperid"],
            dist   # equivalent to SQL embedding <=> %s
        ])

    seen = set()
    good = []

    for row in results:
        dist = row[5]
        if 1 - dist >= MIN_SIM and row[4] not in seen:
            seen.add(row[4])
            good.append(row)

    return good if good else None

async def answer_query(req):
    original_query = req["query"]
    mode = req.get("mode", "simple").lower()
    domain = req.get("domain", "all")

    # ===== AUTOCORRECT =====
    corrected_query = gemini_autocorrect(original_query)
    if corrected_query != original_query:
        print(f"[Retriever] Autocorrected: '{original_query}' → '{corrected_query}'")
    query = corrected_query

    results = retrieve(query, domain)

    
    web_content= await run_web_search(query)
    if not web_content:
        return {
            "original_query": original_query,
            "corrected_query": corrected_query,
            "answer": "Sorry, I couldn't find relevant papers.",
            "references": [],
            "mode": mode
        }
    print(web_content)
    # -------- SIMPLE MODE --------
    if mode == "simple":
        context = "\n\n".join([r[3] for r in results[:8]])
        best = results[0]

        
        prompt = f"""
Answer in 15-20 short sentences using only these sources.
Do NOT mention titles, authors, or years.

Question: {query}
Sources: {context}
web search results: {web_content}
Answer:
"""

        
        
        llm= ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")
        resp= llm.invoke(prompt)

        answer_text = resp.content
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

    if results:
        for row in results:
            pid = row[4]
            if pid in used or len(refs) >= 4:
                continue
            used.add(pid)
            context += row[3] + "\n\n"
            refs.append(make_ref(row[0], row[1], row[2]))

    prompt = f"""
You are an expert researcher.
Give a detailed answer 30-35 lines using only these sources.

Question: {query}
Sources:
{context}
web search results: {web_content}

Answer in clear paragraphs.
End with "References are listed below."
"""

    llm= ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")
    resp= llm.invoke(prompt)

    answer_text = resp.content

    # Summarize
    summary_prompt = f"""
Summarize the above answer in 3-4 lines.
Answer:
{answer_text}
Summary:
"""
    llm= ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")
    resp= llm.invoke(summary_prompt)

    summary_text = resp.content
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