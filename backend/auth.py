"""
auth.py
JWT token creation and decoding. Used by routes/auth.py to issue tokens at login,
and by dependencies.py to validate tokens on protected routes.
"""

from datetime import datetime, timedelta
from typing import Optional

from jose import jwt, JWTError

from config import settings

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    expire = datetime.utcnow() + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "exp": expire, "type": ACCESS_TOKEN_TYPE}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, expires_days: Optional[int] = None) -> str:
    expire = datetime.utcnow() + timedelta(
        days=expires_days or settings.refresh_token_expire_days
    )
    payload = {"sub": subject, "exp": expire, "type": REFRESH_TOKEN_TYPE}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict]:
    """Returns the decoded payload, or None if the token is invalid/expired."""
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
