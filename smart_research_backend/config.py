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
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")  # Added for Tavily

settings = Settings()