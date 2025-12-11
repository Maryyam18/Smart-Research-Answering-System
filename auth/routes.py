from fastapi import APIRouter, HTTPException
from auth.models import SignupModel, LoginModel
from auth.utils import hash_password, verify_password, create_token
from supabaseclient import get_client

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup")
def signup(data: SignupModel):
    supabase = get_client()
    existing = supabase.table("users").select("id").eq("email", data.email).execute()

    if existing.data:
        raise HTTPException(400, "Email already registered")

    hashed = hash_password(data.password)
    result = supabase.table("users").insert({
        "name": data.name,
        "email": data.email,
        "password_hash": hashed
    }).execute()

    if not result.data:
        raise HTTPException(500, "Failed to create user")

    user_id = result.data[0]["id"]


    token = create_token(user_id, data.email)
    return {"message": "Signup successful", "token": token}

@router.post("/login")
def login(data: LoginModel):
    supabase = get_client()

    result = supabase.table("users").select("*").eq("email", data.email).execute()

    if not result.data:
        raise HTTPException(400, "Invalid email or password")

    user = result.data[0]
    

    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(400, "Invalid email or password")

    token = create_token(user["id"], user["email"])
    return {"message": "Login successful", "token": token}
