import hashlib
import secrets
from typing import Optional

from app.core.config import get_settings


def generate_api_key() -> str:
    return f"ml_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    settings = get_settings()
    pepper = settings.API_KEY_PEPPER or "dev-api-key-pepper-change-in-production"
    return hashlib.sha256((api_key + pepper).encode()).hexdigest()


def validate_api_key_format(api_key: str) -> bool:
    return api_key.startswith("ml_") and len(api_key) > 10


def mask_api_key(api_key: str) -> str:
    if len(api_key) <= 8:
        return api_key
    return api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
