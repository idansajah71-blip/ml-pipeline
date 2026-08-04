import re
from typing import Optional


EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)

STRONG_PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{8,}$"
)


def validate_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email))


def validate_strong_password(password: str) -> tuple[bool, Optional[str]]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain a lowercase letter"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain an uppercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain a digit"
    if not re.search(r"[@$!%*?&#]", password):
        return False, "Password must contain a special character"
    return True, None


def sanitize_username(username: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", username)
    return cleaned.lower()


def generate_username_from_email(email: str) -> str:
    local_part = email.split("@")[0]
    return sanitize_username(local_part)
