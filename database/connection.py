import psycopg2
from pgvector.psycopg2 import register_vector
from config import settings

def get_conn():
    conn = psycopg2.connect("postgresql://postgres:FjVNfezkEHRizOhjeiNgzkVMvvLxEAlt@ballast.proxy.rlwy.net:30732/railway")
    register_vector(conn)
    return conn
