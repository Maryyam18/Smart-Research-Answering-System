import json, os
from supabase import create_client

# Supabase connection info
SUPABASE_URL = "https://cujbuzouhjytygwghdjg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN1amJ1em91aGp5dHlnd2doZGpnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ2OTUxMTYsImV4cCI6MjA4MDI3MTExNn0.P0ow8BB44CNl_Y5Hkasw6W06Skv4D9J5jtLF4ndNb7k"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE = "C:/D/semester5/SPM/project/code/code_orginal_for deploymant/Smart-Research-Answering-System/nlp_papers"
DOMAINS = ["NLP", "Quantum Information Retrieval and Information Teleportation", 
           "Quantum Resistant Cryptography and Identity Based Encryption", 
           "VLSI in Power Electronics and Embedded Systems"]

def chunk(text, size=450, overlap=100):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        c = " ".join(words[i:i+size])
        if len(c) > 80: chunks.append(c)
        i += size - overlap
    return chunks or ["Empty content"]

total = 0
for domain in DOMAINS:
    folder = os.path.join(BASE, "json_clean", domain)
    if not os.path.exists(folder): 
        print(f"No JSONs for {domain}")
        continue
    for file in os.listdir(folder):
        if not file.endswith(".json"): 
            continue
        with open(os.path.join(folder, file), encoding="utf-8") as f:
            d = json.load(f)

        text = d.get("abstract", "") + "\n\n"
        for s in d["sections"]:
            text += (s.get("heading", "") + "\n" + s.get("text", "") + "\n\n")

        for ch in chunk(text):
            # Insert into Supabase
            supabase.table("papers").insert({
                "paperid": d["paperid"],
                "title": d["title"],
                "authors": d["authors"][:10],
                "year": d["year"],
                "domain": domain,
                "chunk_text": ch
            }).execute()

        total += 1
        print(f"Added → {d['title'][:65]:65} ({d['year']}) — {domain}")

print(f"\nALL DONE! {total} papers imported from {len(DOMAINS)} domains")
