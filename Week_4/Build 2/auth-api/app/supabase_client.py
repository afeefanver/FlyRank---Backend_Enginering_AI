from supabase import Client, create_client

from app.config import SUPABASE_KEY, SUPABASE_URL


def new_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)