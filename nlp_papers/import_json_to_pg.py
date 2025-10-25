import psycopg2
import json
import os
import logging

# === LOGGING ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger()

# === CONFIG ===
JSON_FOLDER = "E:/5th_Semester/SPM/Smart_Research_Answering_System/nlp_papers/json_clean"
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "hello098",  # CHANGE THIS!
    "dbname": "smart_research"
}

# === 1. CONNECT ===
log.info("Connecting to PostgreSQL...")
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# === 2. CREATE TABLE ===
log.info("Creating table 'papers'...")
cur.execute("""
DROP TABLE IF EXISTS papers;
CREATE TABLE papers (
    id SERIAL PRIMARY KEY,
    paperid TEXT,
    title TEXT,
    authors TEXT[],
    year INT,
    abstract TEXT,
    section_heading TEXT,
    section_text TEXT
);
""")
conn.commit()

# === 3. IMPORT JSON FILES ===
json_files = [f for f in os.listdir(JSON_FOLDER) if f.endswith(".json")]
log.info(f"Found {len(json_files)} JSON files to import.")

for json_file in json_files:
    path = os.path.join(JSON_FOLDER, json_file)
    log.info(f"Loading: {json_file}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for section in data.get("sections", []):
        text = section["text"].strip()
        if len(text) < 50:  # Skip short sections
            continue
        cur.execute("""
            INSERT INTO papers (paperid, title, authors, year, abstract, section_heading, section_text)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            data.get("paperid"),
            data.get("title"),
            data.get("authors"),
            data.get("year"),
            (data.get("abstract") or "")[:2000],
            section.get("heading"),
            text
        ))
    conn.commit()

log.info(f"✅ DONE! Imported {len(json_files)} papers into PostgreSQL.")
log.info("Table 'papers' is ready for embedding.")

cur.close()
conn.close()
