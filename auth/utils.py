import bcrypt
from jose import jwt
from datetime import datetime, timedelta
from config import settings

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(user_id: int, email: str):
    payload = {
        "uid": user_id,
        "sub": email,
        "exp": datetime.utcnow() + timedelta(hours=8)
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGO)

def verify_token(token: str):
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGO])
