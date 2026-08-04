import hashlib
import secrets
from typing import Optional


def generate_api_key() -> str:
    return f"ml_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def validate_api_key_format(api_key: str) -> bool:
    return api_key.startswith("ml_") and len(api_key) > 10


def mask_api_key(api_key: str) -> str:
    if len(api_key) <= 8:
        return api_key
    return api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
