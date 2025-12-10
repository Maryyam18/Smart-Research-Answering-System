from fastapi import APIRouter, HTTPException
from auth.models import SignupModel, LoginModel
from auth.utils import hash_password, verify_password, create_token
from database.connection import get_conn

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup")
def signup(data: SignupModel):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE email=%s", (data.email,))
    if cur.fetchone():
        raise HTTPException(400, "Email already registered")

    hashed = hash_password(data.password)

    cur.execute("""
        INSERT INTO users(name, email, password_hash)
        VALUES (%s, %s, %s)
        RETURNING id
    """, (data.name, data.email, hashed))

    user_id = cur.fetchone()[0]
    conn.commit()
    cur.close(); conn.close()

    token = create_token(user_id, data.email)
    return {"message": "Signup successful", "token": token}

@router.post("/login")
def login(data: LoginModel):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, password_hash FROM users WHERE email=%s", (data.email,))
    row = cur.fetchone()

    if not row:
        raise HTTPException(400, "Invalid email or password")

    user_id, stored_hash = row

    if not verify_password(data.password, stored_hash):
        raise HTTPException(400, "Invalid email or password")

    token = create_token(user_id, data.email)
    return {"message": "Login successful", "token": token}
