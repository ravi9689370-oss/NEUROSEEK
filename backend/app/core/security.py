"""Authentication and security utilities."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt
from passlib.context import CryptContext
from pydantic import SecretStr

from app.core.config import get_settings


settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.auth.access_token_expire_minutes
        )
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    if extra_claims:
        to_encode.update(extra_claims)
    
    return jwt.encode(
        to_encode,
        settings.auth.secret_key.get_secret_value(),
        algorithm=settings.auth.algorithm,
    )


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.auth.refresh_token_expire_days
    )
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    
    return jwt.encode(
        to_encode,
        settings.auth.secret_key.get_secret_value(),
        algorithm=settings.auth.algorithm,
    )


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.auth.secret_key.get_secret_value(),
        algorithms=[settings.auth.algorithm],
    )


def decode_access_token(token: str) -> Optional[str]:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return payload.get("sub")
    except jwt.JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[str]:
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            return None
        return payload.get("sub")
    except jwt.JWTError:
        return None