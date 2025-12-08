import psycopg2
from pgvector.psycopg2 import register_vector
from config import settings

def get_conn():
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        dbname=settings.DB_NAME,
        sslmode='require'
    )
    register_vector(conn)
    return conn
