import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Any

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt (for short passwords like user passwords)."""
    # Truncate to 72 bytes for bcrypt compatibility
    return pwd_context.hash(password[:72])


def hash_secret(secret: str) -> str:
    """Hash an API key or secret using SHA256 (for longer secrets)."""
    return hashlib.sha256(secret.encode()).hexdigest()


def verify_secret(secret: str, hashed_secret: str) -> bool:
    """Verify a secret against its SHA256 hash."""
    return hashlib.sha256(secret.encode()).hexdigest() == hashed_secret


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def generate_client_id() -> str:
    """Generate a unique client ID."""
    return secrets.token_hex(16)


def generate_client_secret() -> str:
    """Generate a secure client secret."""
    return secrets.token_urlsafe(48)


def generate_jwt_secret() -> str:
    """Generate a secure JWT secret for a project."""
    return secrets.token_urlsafe(32)


def create_access_token(
    data: dict[str, Any],
    secret_key: str,
    algorithm: str = "HS256",
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    now = datetime.utcnow()

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


def create_refresh_token(
    data: dict[str, Any],
    secret_key: str,
    algorithm: str = "HS256",
) -> str:
    """Create a JWT refresh token (longer expiration)."""
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + timedelta(days=7)  # Refresh tokens last 7 days

    to_encode.update({"exp": expire, "iat": now, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


def decode_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256",
) -> dict[str, Any] | None:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except JWTError:
        return None


def verify_api_key(api_key: str, api_key_hash: str) -> bool:
    """Verify an API key against its hash."""
    return verify_secret(api_key, api_key_hash)


def verify_client_secret(client_secret: str, client_secret_hash: str) -> bool:
    """Verify a client secret against its hash."""
    return verify_secret(client_secret, client_secret_hash)
