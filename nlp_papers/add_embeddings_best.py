import psycopg2
from sentence_transformers import SentenceTransformer
from pgvector.psycopg2 import register_vector
import numpy as np
from tqdm import tqdm
import logging

# === LOGGING ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger()

# === CONFIG ===
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "hello098",  # CHANGE THIS!
    "dbname": "smart_research"
}
MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE = 400
OVERLAP = 100
BATCH_SIZE = 32

# === 1. LOAD EMBEDDING MODEL ===
log.info("Loading embedding model...")
model = SentenceTransformer(MODEL_NAME, device='cpu')  # Use 'cuda' if GPU available

# === 2. CONNECT TO DATABASE ===
log.info("Connecting to PostgreSQL database...")
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# Ensure pgvector extension exists before registering
cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
conn.commit()

# Register the vector type
register_vector(conn)
log.info("pgvector extension verified and registered successfully.")

# === 3. ADD EMBEDDING COLUMN IF NEEDED ===
log.info("Ensuring embedding column exists...")
cur.execute("ALTER TABLE papers ADD COLUMN IF NOT EXISTS embedding VECTOR(384);")
conn.commit()

# === 4. CHUNK FUNCTION ===
def chunk_text(text):
    if len(text) <= CHUNK_SIZE:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        start = end - OVERLAP
        if end >= len(text):
            break
    return chunks

# === 5. FETCH UNEMBEDDED ROWS ===
cur.execute("SELECT id, section_text FROM papers WHERE embedding IS NULL;")
rows = cur.fetchall()
log.info(f"Found {len(rows)} rows to embed.")

# === 6. PROCESS & EMBED IN BATCHES ===
batch_texts, batch_ids = [], []

for row_id, text in tqdm(rows, desc="Embedding Chunks"):
    chunks = chunk_text(text)
    batch_texts.extend(chunks)
    batch_ids.extend([row_id] * len(chunks))

    if len(batch_texts) >= BATCH_SIZE:
        embeddings = model.encode(batch_texts, normalize_embeddings=True, batch_size=BATCH_SIZE, show_progress_bar=False)
        for emb, pid in zip(embeddings, batch_ids):
            cur.execute("UPDATE papers SET embedding = %s WHERE id = %s;", (emb.tolist(), pid))
        conn.commit()
        batch_texts, batch_ids = [], []

# Process final leftover batch
if batch_texts:
    embeddings = model.encode(batch_texts, normalize_embeddings=True, batch_size=BATCH_SIZE)
    for emb, pid in zip(embeddings, batch_ids):
        cur.execute("UPDATE papers SET embedding = %s WHERE id = %s;", (emb.tolist(), pid))
    conn.commit()

# === 7. CREATE VECTOR INDEX ===
log.info("Creating IVFFlat index for fast similarity search...")
cur.execute("""
    CREATE INDEX IF NOT EXISTS papers_embedding_idx 
    ON papers USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
""")
conn.commit()

log.info("✅ EMBEDDINGS + INDEX COMPLETED SUCCESSFULLY!")
log.info("System is ready for semantic (RAG) search.")

# === 8. CLEANUP ===
cur.close()
conn.close()
