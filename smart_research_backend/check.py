import psycopg2
from pgvector.psycopg2 import register_vector

conn = psycopg2.connect(
    host="localhost",
    port=5433,
    user="postgres",
    password="hello098",
    dbname="smart_research"
)
register_vector(conn)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM papers;")
print("Total papers:", cur.fetchone()[0])
cur.close()
conn.close()
