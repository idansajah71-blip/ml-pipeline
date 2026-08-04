import hashlib
import hmac
import secrets
from typing import Optional


def generate_session_id() -> str:
    return secrets.token_urlsafe(32)


def hash_session_id(session_id: str) -> str:
    return hashlib.sha256(session_id.encode()).hexdigest()


def generate_csrf_token() -> str:
    return secrets.token_hex(32)


def verify_csrf_token(token: str, expected: str) -> bool:
    return hmac.compare_digest(token, expected)


def generate_state_param() -> str:
    return secrets.token_urlsafe(16)
