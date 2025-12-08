from supabase import create_client
from config import settings

if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment")

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
