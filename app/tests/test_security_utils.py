import pytest
from datetime import timedelta
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    generate_api_key,
)


class TestPasswordHashing:
    def test_hash_password(self):
        password = "test_password_123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_correct_password(self):
        password = "secret_password"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        password = "secret_password"
        hashed = get_password_hash(password)
        assert verify_password("wrong_password", hashed) is False

    def test_different_hashes_for_same_password(self):
        password = "same_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2

    def test_empty_password(self):
        hashed = get_password_hash("")
        assert verify_password("", hashed) is True

    def test_unicode_password(self):
        password = "пароль_тест_🔐"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True


class TestJWT:
    def test_create_access_token(self):
        token = create_access_token({"sub": "user-id-123"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_with_custom_expiry(self):
        token = create_access_token(
            {"sub": "user-id"}, expires_delta=timedelta(hours=1)
        )
        assert isinstance(token, str)

    def test_token_contains_data(self):
        from jose import jwt
        from app.core.config import get_settings

        settings = get_settings()
        token = create_access_token({"sub": "test-user", "role": "admin"})
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "test-user"
        assert payload["role"] == "admin"

    def test_token_has_expiry(self):
        from jose import jwt
        from app.core.config import get_settings

        settings = get_settings()
        token = create_access_token({"sub": "test-user"})
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert "exp" in payload

    def test_invalid_token_raises_error(self):
        from jose import JWTError
        from app.core.config import get_settings

        settings = get_settings()
        with pytest.raises(JWTError):
            jwt.decode("invalid.token.here", settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


class TestAPIKey:
    def test_generate_api_key(self):
        key = generate_api_key()
        assert key.startswith("ml_")
        assert len(key) > 10

    def test_unique_api_keys(self):
        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100
