# 3_import_to_db.py
import json, os, psycopg2

BASE = "E:/5th_Semester/SPM/Smart_Research_Answering_System/nlp_papers"
DOMAINS = ["NLP", "Quantum Information Retrieval and Information Teleportation", "Quantum Resistant Cryptography and Identity Based Encryption", "VLSI in Power Electronics and Embedded Systems"]

DB = {"host": "localhost", "port": 5432, "user": "postgres", "password": "hello098", "dbname": "smart_research"}

def chunk(text, size=450, overlap=100):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        c = " ".join(words[i:i+size])
        if len(c) > 80: chunks.append(c)
        i += size - overlap
    return chunks or ["Empty content"]

conn = psycopg2.connect(**DB)
cur = conn.cursor()

# Only run DROP when you want fresh start
cur.execute("DROP TABLE IF EXISTS papers CASCADE;")
cur.execute("""
CREATE TABLE papers (
    id SERIAL PRIMARY KEY,
    paperid TEXT,
    title TEXT,
    authors TEXT[],
    year INT,
    domain TEXT,
    chunk_text TEXT,
    embedding VECTOR(384)
);
CREATE INDEX IF NOT EXISTS idx_emb ON papers USING ivfflat (embedding vector_cosine_ops) WITH (lists = 1000);
""")
conn.commit()

total = 0
for domain in DOMAINS:
    folder = os.path.join(BASE, "json_clean", domain)
    if not os.path.exists(folder): 
        print(f"No JSONs for {domain}")
        continue
    for file in os.listdir(folder):
        if not file.endswith(".json"): continue
        with open(os.path.join(folder, file), encoding="utf-8") as f:
            d = json.load(f)

        text = d.get("abstract", "") + "\n\n"
        for s in d["sections"]:
            text += (s.get("heading", "") + "\n" + s.get("text", "") + "\n\n")

        for chunk in chunk(text):
            cur.execute("""
                INSERT INTO papers (paperid, title, authors, year, domain, chunk_text)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (d["paperid"], d["title"], d["authors"][:10], d["year"], domain, chunk))
        total += 1
        print(f"Added → {d['title'][:65]:65} ({d['year']}) — {domain}")

    conn.commit()

print(f"\nALL DONE! {total} papers imported from {len(DOMAINS)} domains")
cur.close(); conn.close()