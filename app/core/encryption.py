import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class EncryptionService:
    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or settings.JWT_SECRET_KEY
        self._fernet = None

    def _get_fernet(self) -> Fernet:
        if self._fernet is None:
            key = self._derive_key(self.master_key)
            self._fernet = Fernet(key)
        return self._fernet

    def _derive_key(self, password: str) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'ml-pipeline-salt',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def encrypt(self, data: str) -> str:
        fernet = self._get_fernet()
        encrypted = fernet.encrypt(data.encode())
        return encrypted.decode()

    def decrypt(self, encrypted_data: str) -> str:
        fernet = self._get_fernet()
        decrypted = fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()

    def encrypt_dict(self, data: dict) -> str:
        import json
        json_str = json.dumps(data)
        return self.encrypt(json_str)

    def decrypt_dict(self, encrypted_data: str) -> dict:
        import json
        decrypted = self.decrypt(encrypted_data)
        return json.loads(decrypted)

    def hash_sensitive_data(self, data: str) -> str:
        import hashlib
        return hashlib.sha256((data + self.master_key).encode()).hexdigest()

    def mask_sensitive_data(self, data: str, visible_chars: int = 4) -> str:
        if len(data) <= visible_chars:
            return "*" * len(data)
        return "*" * (len(data) - visible_chars) + data[-visible_chars:]

    def mask_email(self, email: str) -> str:
        parts = email.split("@")
        if len(parts) != 2:
            return self.mask_sensitive_data(email)

        username, domain = parts
        if len(username) <= 2:
            masked_username = username[0] + "***"
        else:
            masked_username = username[:2] + "***" + username[-1]

        return f"{masked_username}@{domain}"

    def mask_phone(self, phone: str) -> str:
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) < 4:
            return phone
        return "***-***-" + digits[-4:]


encryption_service = EncryptionService()
