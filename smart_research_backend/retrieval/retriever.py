from sentence_transformers import SentenceTransformer
from groq import Groq
from database.connection import get_conn
from autocorrect import gemini_autocorrect
from config import settings
from langchain_community.tools.tavily_search import TavilySearchResults

TOP_K = 20
MIN_SIM = 0.64

print("Loading model BAAI/bge-small-en-v1.5...")
model = SentenceTransformer("BAAI/bge-small-en-v1.5")
client = Groq(api_key=settings.GROQ_API_KEY)

# Tavily search tool
search_tool = TavilySearchResults(
    max_results=5,
    search_depth="advanced",
    include_raw_content=True,
    include_domains=["arxiv.org", "semanticscholar.org", "researchgate.net", "aclanthology.org", "nature.com", "sciencedirect.com"],
    api_key=settings.TAVILY_API_KEY
)


def chunk(text: str, size: int = 450, overlap: int = 100):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i:i + size]
        chunk_text = " ".join(chunk_words)
        if len(chunk_text) > 80:
            chunks.append(chunk_text)
        i += size - overlap
    return chunks if chunks else ["Empty content"]


def detect_domain(query: str) -> str:
    prompt = f"Return only the main academic domain of this query in 1-4 words. Examples: NLP, Quantum Computing, Machine Learning, VLSI, Robotics.\nQuery: {query}\nDomain:"
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=15,
            temperature=0
        )
        domain = resp.choices[0].message.content.strip().strip('"').strip("'")
        return domain if domain else "General Research"
    except Exception as e:
        print(f"[Domain Detection Error] {e}")
        return "General Research"


def add_dynamic_papers(session_id: int, query: str, domain: str):
    conn = get_conn()
    cur = conn.cursor()

    search_query = f"\"{query}\" {domain} research paper filetype:pdf"
    try:
        results = search_tool.invoke({"query": search_query})
    except Exception as e:
        print(f"[Tavily Error] {e}")
        cur.close()
        conn.close()
        return 0

    added = 0
    for item in results:
        url = item.get("url")
        raw_content = item.get("content", "")
        title = item.get("title", "Untitled Paper")

        if not url or not raw_content or len(raw_content) < 200:
            continue

        # Avoid duplicate in same session
        cur.execute("SELECT 1 FROM dynamic_papers WHERE session_id=%s AND url=%s", (session_id, url))
        if cur.fetchone():
            continue

        # Insert paper
        cur.execute(
            "INSERT INTO dynamic_papers (session_id, url, title, content) VALUES (%s, %s, %s, %s) RETURNING id",
            (session_id, url, title, raw_content)
        )
        paper_id = cur.fetchone()[0]

        # Chunk and embed
        chunks = chunk(raw_content)
        texts_to_embed = []
        for idx, ch in enumerate(chunks):
            enriched = f"Title: {title} | Domain: {domain} | {ch}" if idx == 0 else ch
            texts_to_embed.append(enriched)

        if not texts_to_embed:
            continue

        embeddings = model.encode(texts_to_embed, normalize_embeddings=True, batch_size=8)

        for idx, (text, vector) in enumerate(zip(texts_to_embed, embeddings)):
            cur.execute(
                """INSERT INTO dynamic_chunks 
                   (paper_id, chunk_text, embedding, chunk_index) 
                   VALUES (%s, %s, %s, %s)""",
                (paper_id, text, vector.tolist(), idx)
            )

        added += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"[Dynamic] Added {added} new papers for session {session_id}")
    return added


def retrieve(query: str, session_id: int):
    conn = get_conn()
    cur = conn.cursor()
    q_emb = model.encode(query, normalize_embeddings=True)

    cur.execute("""
        SELECT dc.chunk_text, dp.url, dc.embedding <=> CAST(%s AS vector) AS dist
        FROM dynamic_chunks dc
        JOIN dynamic_papers dp ON dc.paper_id = dp.id
        WHERE dp.session_id = %s
        ORDER BY dist ASC
        LIMIT %s
    """, (q_emb.tolist(), session_id, TOP_K))

    results = cur.fetchall()
    cur.close()
    conn.close()

    seen_urls = set()
    good_chunks = []
    for chunk_text, url, dist in results:
        sim = 1 - dist
        if sim >= MIN_SIM and url not in seen_urls:
            seen_urls.add(url)
            good_chunks.append((chunk_text, url))
    return good_chunks


def answer_query(req):
    original_query = req["query"]
    mode = req.get("mode", "simple").lower()
    session_id = req["session_id"]

    # Autocorrect (bypass if quota issue)
    corrected_query = gemini_autocorrect(original_query)
    if corrected_query != original_query:
        print(f"[Autocorrect] '{original_query}' → '{corrected_query}'")
    query = corrected_query

    # Detect domain
    domain = detect_domain(query)
    print(f"[Domain Detected] {domain}")

    # Search & add papers
    added = add_dynamic_papers(session_id, query, domain)
    if added == 0:
        print("[Warning] No new papers added – using existing ones if any")

    # Retrieve relevant chunks
    results = retrieve(query, session_id)

    if not results:
        answer = "Sorry, I couldn't find any relevant research papers for your query right now. Try asking something more specific or from a popular research area."
        return {
            "original_query": original_query,
            "corrected_query": corrected_query,
            "answer": answer,
            "references": [],
            "mode": mode
        }

    context = "\n\n".join([item[0] for item in results])
    refs = list({item[1] for item in results})  # unique URLs

    if mode == "simple":
        best_url = results[0][1]
        prompt = f"""Answer the question in 3-4 short sentences using only the sources below. 
Do NOT mention URLs, titles, or authors in the answer.

Question: {query}

Sources:
{context}

Answer:"""

        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3
        )
        answer_text = resp.choices[0].message.content.strip()
        answer_text += f"\n\nReference: {best_url}"

        return {
            "original_query": original_query,
            "corrected_query": corrected_query,
            "answer": answer_text,
            "references": [best_url],
            "mode": "simple"
        }

    # Deep mode with headings
    prompt = f"""You are an expert academic researcher. Write a detailed, accurate answer using only the sources below.
Organize the response beautifully with these headings:
- Introduction
- Key Concepts
- Recent Advances
- Challenges and Future Directions

Question: {query}

Sources:
{context}

Write in clear, engaging paragraphs under each heading. Keep it professional and easy to read. At the very end, write exactly this line:
References are listed below."""

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
        temperature=0.4
    )
    answer_text = resp.choices[0].message.content.strip()

    # Summary (as Conclusion heading)
    summary_prompt = f"Summarize this answer in 3-4 lines only (focus on key takeaways):\n\n{answer_text}\n\nSummary:"
    summary_resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": summary_prompt}],
        max_tokens=150
    )
    summary = summary_resp.choices[0].message.content.strip()

    final_answer = f"{answer_text}\n\nConclusion:\n{summary}\n\nReferences:\n" + "\n".join(f"• {url}" for url in refs)

    return {
        "original_query": original_query,
        "corrected_query": corrected_query,
        "answer": final_answer,
        "references": refs,
        "mode": "deep"
    }