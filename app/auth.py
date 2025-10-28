import os
import time
from typing import Optional

import jwt
from passlib.context import CryptContext

# Use pbkdf2_sha256 as default to avoid bcrypt 72-byte limitation in some envs
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

SECRET = os.getenv("JWT_SECRET", "dev-secret")
ALGORITHM = "HS256"
EXP_SECONDS = 60 * 60 * 24  # 1 day


def create_access_token(user_id: int, role: str, expires_delta: Optional[int] = None) -> str:
    now = int(time.time())
    exp = now + (expires_delta or EXP_SECONDS)
    payload = {"sub": str(user_id), "role": role, "iat": now, "exp": exp}
    token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
    return token


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
