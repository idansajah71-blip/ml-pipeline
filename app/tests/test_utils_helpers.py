"""Tests for small utility modules that had 0% coverage (coverage audit)."""
import pytest

from app.utils.pagination import (
    PaginationParams,
    PaginatedResult,
    paginate_query,
    create_paginated_response,
)
from app.utils.retry import retry, async_retry
from app.utils import api_keys
from app.utils.validation import (
    validate_email,
    validate_strong_password,
    sanitize_username,
    generate_username_from_email,
)
from app.core.rate_limit import RateLimitConfig, rate_limit_config
from app.core import exceptions
from app.schemas.responses import (
    success_response,
    error_response,
    PaginatedResponse,
)


# ── pagination ─────────────────────────────────────────────────────────────

class TestPaginationParams:
    def test_offset_limit(self):
        p = PaginationParams(page=3, per_page=10)
        assert p.offset == 20
        assert p.limit == 10

    def test_defaults(self):
        p = PaginationParams()
        assert p.page == 1
        assert p.per_page == 20


class TestPaginatedResult:
    def test_pages_and_navigation(self):
        r = PaginatedResult(items=[1, 2, 3], total=45, page=1, per_page=10)
        assert r.pages == 5
        assert r.has_next is True
        assert r.has_prev is False
        assert r.next_page == 2
        assert r.prev_page is None

    def test_last_page_navigation(self):
        r = PaginatedResult(items=[], total=45, page=5, per_page=10)
        assert r.has_next is False
        assert r.next_page is None
        assert r.prev_page == 4

    def test_zero_per_page_no_division_error(self):
        r = PaginatedResult(items=[], total=10, per_page=0)
        assert r.pages == 0
        assert r.has_next is False


def test_paginate_query():
    class FakeQuery:
        def offset(self, n):
            self._off = n
            return self

        def limit(self, n):
            self._lim = n
            return self

    q = FakeQuery()
    out = paginate_query(q, PaginationParams(page=2, per_page=5))
    assert out is q
    assert q._off == 5
    assert q._lim == 5


def test_create_paginated_response():
    resp = create_paginated_response([1, 2], 42, PaginationParams(page=1, per_page=10))
    assert resp["items"] == [1, 2]
    assert resp["total"] == 42
    assert resp["pages"] == 5
    assert resp["has_next"] is True
    assert resp["has_prev"] is False


# ── retry ──────────────────────────────────────────────────────────────────

class TestRetry:
    def test_succeeds_first_attempt(self):
        calls = []

        @retry(max_retries=2, delay=0)
        def fn():
            calls.append(1)
            return "ok"

        assert fn() == "ok"
        assert len(calls) == 1

    def test_retries_then_succeeds(self):
        calls = []

        @retry(max_retries=3, delay=0)
        def fn():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("boom")
            return "recovered"

        assert fn() == "recovered"
        assert len(calls) == 3

    def test_raises_after_exhausting_retries(self):
        @retry(max_retries=2, delay=0)
        def fn():
            raise RuntimeError("always fails")

        with pytest.raises(RuntimeError, match="always fails"):
            fn()

    def test_only_retries_specified_exceptions(self):
        calls = []

        @retry(max_retries=3, delay=0, exceptions=(ValueError,))
        def fn():
            calls.append(1)
            raise TypeError("not retried")

        with pytest.raises(TypeError):
            fn()
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_async_retry(self):
        calls = []

        @async_retry(max_retries=2, delay=0)
        async def fn():
            calls.append(1)
            if len(calls) < 2:
                raise ConnectionError("boom")
            return "ok"

        assert await fn() == "ok"
        assert len(calls) == 2


# ── api_keys ───────────────────────────────────────────────────────────────

class TestApiKeys:
    def test_generate_and_hash(self):
        key = api_keys.generate_api_key()
        assert key.startswith("ml_")
        assert api_keys.hash_api_key(key) == api_keys.hash_api_key(key)
        assert api_keys.hash_api_key(key) != api_keys.hash_api_key(key + "x")

    def test_validate_format(self):
        assert api_keys.validate_api_key_format("ml_" + "a" * 20)
        assert not api_keys.validate_api_key_format("short")
        assert not api_keys.validate_api_key_format("no_prefix_" + "a" * 20)

    def test_mask_api_key(self):
        masked = api_keys.mask_api_key("ml_" + "a" * 40)
        assert masked.startswith("ml_")
        assert masked.endswith("aaaa")
        assert "*" in masked
        assert "ml_" + "a" * 40 != masked
        # Short keys returned unchanged
        assert api_keys.mask_api_key("shortkey") == "shortkey"


# ── validation ─────────────────────────────────────────────────────────────

class TestValidation:
    def test_validate_email(self):
        assert validate_email("user@example.com")
        assert validate_email("a.b+c@sub.domain.co.id")
        assert not validate_email("not-an-email")
        assert not validate_email("user@nodot")

    def test_strong_password(self):
        ok, err = validate_strong_password("Str0ng!Pass")
        assert ok is True
        assert err is None
        assert validate_strong_password("short")[0] is False
        assert validate_strong_password("nouppercase1!")[0] is False
        assert validate_strong_password("NOLOWER1!")[0] is False
        assert validate_strong_password("NoSpecial1")[0] is False
        assert validate_strong_password("NoDigit!")[0] is False

    def test_sanitize_username(self):
        assert sanitize_username("Hello World!") == "helloworld"
        assert sanitize_username("User_Name-123") == "user_name-123"

    def test_generate_username_from_email(self):
        assert generate_username_from_email("John.Doe@Example.com") == "johndoe"


# ── rate_limit config ──────────────────────────────────────────────────────

class TestRateLimitConfig:
    def test_defaults(self):
        cfg = RateLimitConfig()
        assert cfg.default_limit == 100
        assert cfg.default_window == 60
        assert "/api/v1/auth/login" in cfg.custom_limits
        assert cfg.custom_limits["/api/v1/auth/login"] == (5, 60)

    def test_singleton(self):
        assert rate_limit_config.default_limit == 100


# ── exceptions ─────────────────────────────────────────────────────────────

class TestAppExceptions:
    def test_status_codes(self):
        assert exceptions.NotFoundException().status_code == 404
        assert exceptions.ForbiddenException().status_code == 403
        assert exceptions.BadRequestException().status_code == 400
        assert exceptions.ConflictException().status_code == 409
        assert exceptions.RateLimitException().status_code == 429

    def test_not_found_detail_includes_resource(self):
        exc = exceptions.NotFoundException("Dataset", "abc-123")
        assert "Dataset not found" in exc.detail
        assert "abc-123" in exc.detail

    @pytest.mark.asyncio
    async def test_app_exception_handler(self):
        exc = exceptions.BadRequestException("bad payload")
        response = await exceptions.app_exception_handler(None, exc)
        assert response.status_code == 400
        assert response.body == b'{"detail":"bad payload"}'


# ── responses schema ───────────────────────────────────────────────────────

class TestResponses:
    def test_success_response(self):
        resp = success_response({"id": 1})
        assert resp["success"] is True
        assert resp["data"] == {"id": 1}
        assert resp["message"] == "Success"

    def test_error_response(self):
        resp = error_response("Something broke", ["e1", "e2"])
        assert resp["success"] is False
        assert resp["errors"] == ["e1", "e2"]
        assert resp["message"] == "Something broke"

    def test_paginated_response_model(self):
        r = PaginatedResponse(items=[1], total=100, page=1, per_page=10)
        assert r.items == [1]
        assert r.total == 100
        assert r.per_page == 10
