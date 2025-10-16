from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(sub: str) -> str:
    now = datetime.now(tz=timezone.utc)
    exp = now + settings.access_token_timedelta
    payload: dict[str, Any] = {"sub": sub, "exp": int(exp.timestamp())}
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)
    return token


def decode_token(token: str) -> Optional[dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        return payload
    except JWTError:
        return None
