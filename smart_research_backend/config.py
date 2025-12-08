import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    JWT_SECRET = os.getenv("JWT_SECRET")
    JWT_ALGO = os.getenv("JWT_ALGORITHM")

    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME")
    
SUPABASE_URL = "https://cujbuzouhjytygwghdjg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN1amJ1em91aGp5dHlnd2doZGpnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ2OTUxMTYsImV4cCI6MjA4MDI3MTExNn0.P0ow8BB44CNl_Y5Hkasw6W06Skv4D9J5jtLF4ndNb7k"


settings = Settings()
