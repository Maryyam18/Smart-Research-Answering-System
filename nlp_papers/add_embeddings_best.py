import psycopg2
from sentence_transformers import SentenceTransformer
from pgvector.psycopg2 import register_vector
import numpy as np
from tqdm import tqdm
import logging

# === LOGGING ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger()

# === CONFIG ===
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "hello098",
    "dbname": "smart_research"
}
MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE = 400
OVERLAP = 100
BATCH_SIZE = 32

# === 1. LOAD MODEL ===
log.info("Loading embedding model...")
model = SentenceTransformer(MODEL_NAME, device='cpu')
log.info("Model loaded.")

# === 2. CONNECT & SETUP PGVECTOR ===
log.info("Connecting to PostgreSQL...")
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# Enable pgvector
# cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
# conn.commit()
log.info("pgvector already enabled.")

# Register vector type for psycopg2
register_vector(conn)
log.info("pgvector ready.")

# === 3. FIX EMBEDDING COLUMN (CRITICAL!) ===
log.info("Fixing embedding column to VECTOR(384)...")
cur.execute("""
    ALTER TABLE papers 
    DROP COLUMN IF EXISTS embedding;
""")
cur.execute("""
    ALTER TABLE papers 
    ADD COLUMN embedding VECTOR(384);
""")
conn.commit()
log.info("Embedding column re-created as VECTOR(384).")

# === 4. CHUNK FUNCTION ===
def chunk_text(text):
    if not text or len(text.strip()) == 0:
        return []
    text = text.strip()
    if len(text) <= CHUNK_SIZE:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - OVERLAP
        if end >= len(text):
            break
    return chunks

# === 5. GET ALL ROWS (RE-EMBED ALL) ===
log.info("Fetching all section texts for embedding...")
cur.execute("SELECT id, section_text FROM papers;")
rows = cur.fetchall()
log.info(f"Found {len(rows)} sections to embed.")

# === 6. EMBED IN BATCHES ===
batch_texts = []
batch_ids = []

for row_id, text in tqdm(rows, desc="Embedding", unit="section"):
    chunks = chunk_text(text)
    if not chunks:
        continue
    batch_texts.extend(chunks)
    batch_ids.extend([row_id] * len(chunks))

    # Process batch
    if len(batch_texts) >= BATCH_SIZE:
        log.info(f"Encoding batch of {len(batch_texts)} chunks...")
        embeddings = model.encode(
            batch_texts,
            normalize_embeddings=True,
            batch_size=BATCH_SIZE,
            show_progress_bar=False
        )
        for emb, pid in zip(embeddings, batch_ids):
            cur.execute(
                "UPDATE papers SET embedding = %s WHERE id = %s;",
                (emb.tolist(), pid)
            )
        conn.commit()
        batch_texts, batch_ids = [], []

# Final batch
if batch_texts:
    log.info(f"Encoding final batch of {len(batch_texts)} chunks...")
    embeddings = model.encode(
        batch_texts,
        normalize_embeddings=True,
        batch_size=BATCH_SIZE,
        show_progress_bar=False
    )
    for emb, pid in zip(embeddings, batch_ids):
        cur.execute(
            "UPDATE papers SET embedding = %s WHERE id = %s;",
            (emb.tolist(), pid)
        )
    conn.commit()

# === 7. CREATE INDEX ===
log.info("Creating vector index...")
cur.execute("""
    DROP INDEX IF EXISTS papers_embedding_idx;
""")
cur.execute("""
    CREATE INDEX papers_embedding_idx 
    ON papers USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);
""")
conn.commit()
log.info("Index created.")

# === 8. DONE ===
log.info("EMBEDDINGS + INDEX COMPLETED SUCCESSFULLY!")
log.info("Your RAG system is READY!")

cur.close()
conn.close()