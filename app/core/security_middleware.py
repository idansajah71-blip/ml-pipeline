import time
from typing import Dict, Optional, Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import re

from app.core.logging import get_logger
from app.core.redis import get_redis

logger = get_logger(__name__)

TIER_UPLOAD_LIMITS_MB = {
    "free": 10,
    "starter": 50,
    "pro": 200,
    "enterprise": 1000,
}

TIER_TRAINING_LIMITS = {
    "free": {"daily": 5, "monthly": 50},
    "starter": {"daily": 20, "monthly": 200},
    "pro": {"daily": 100, "monthly": 1000},
    "enterprise": {"daily": 500, "monthly": 5000},
}

TIER_RATE_LIMITS = {
    "free": {"rpm": 60, "burst": 10},
    "starter": {"rpm": 300, "burst": 50},
    "pro": {"rpm": 1000, "burst": 200},
    "enterprise": {"rpm": 5000, "burst": 1000},
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        default_limit: int = 100,
        default_window: int = 60,
        custom_limits: Optional[Dict[str, tuple]] = None,
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.default_window = default_window
        self.custom_limits = custom_limits or {}

    def get_client_key(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"rate_limit:user:{user_id}"
        return f"rate_limit:ip:{ip}"

    def get_rate_limit(self, path: str) -> tuple:
        for pattern, limits in self.custom_limits.items():
            if re.match(pattern, path):
                return limits
        return self.default_limit, self.default_window

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/health", "/metrics", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        client_key = self.get_client_key(request)
        limit, window = self.get_rate_limit(request.url.path)

        redis_client = await get_redis()

        if redis_client:
            try:
                current = await redis_client.get(client_key)
                if current and int(current) >= limit:
                    retry_after = await redis_client.ttl(client_key)
                    logger.warning(
                        f"Rate limit exceeded for {client_key}",
                        path=request.url.path,
                        limit=limit,
                        window=window,
                    )
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"detail": "Rate limit exceeded. Please try again later."},
                        headers={"Retry-After": str(max(retry_after, window))},
                    )

                pipe = redis_client.pipeline()
                pipe.incr(client_key)
                pipe.expire(client_key, window)
                results = await pipe.execute()

                remaining = max(0, limit - results[0])
            except Exception as e:
                logger.warning(f"Redis rate limit error: {e}")
                remaining = limit
        else:
            remaining = limit

        response = await call_next(request)

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response


class UploadSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, default_max_mb: int = 100):
        super().__init__(app)
        self.default_max_mb = default_max_mb

    def get_user_tier(self, request: Request) -> str:
        return getattr(request.state, "user_tier", "free")

    def get_max_upload_size_mb(self, tier: str) -> int:
        return TIER_UPLOAD_LIMITS_MB.get(tier, TIER_UPLOAD_LIMITS_MB["free"])

    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")

            if "multipart/form-data" in content_type:
                content_length = request.headers.get("content-length")

                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    tier = self.get_user_tier(request)
                    max_size_mb = self.get_max_upload_size_mb(tier)

                    if size_mb > max_size_mb:
                        logger.warning(
                            f"Upload size exceeded: {size_mb:.1f}MB > {max_size_mb}MB (tier: {tier})",
                            path=request.url.path,
                        )
                        return JSONResponse(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            content={
                                "detail": f"Upload size exceeds limit. Maximum allowed: {max_size_mb}MB for {tier} tier.",
                                "max_size_mb": max_size_mb,
                                "tier": tier,
                            },
                        )

        return await call_next(request)


class TrainingQuotaMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and "/train" in request.url.path:
            user_id = getattr(request.state, "user_id", None)
            if user_id:
                redis_client = await get_redis()
                if redis_client:
                    try:
                        tier = getattr(request.state, "user_tier", "free")
                        limits = TIER_TRAINING_LIMITS.get(tier, TIER_TRAINING_LIMITS["free"])

                        daily_key = f"training:daily:{user_id}"
                        monthly_key = f"training:monthly:{user_id}"

                        daily_count = await redis_client.get(daily_key)
                        monthly_count = await redis_client.get(monthly_key)

                        daily_count = int(daily_count) if daily_count else 0
                        monthly_count = int(monthly_count) if monthly_count else 0

                        if daily_count >= limits["daily"]:
                            return JSONResponse(
                                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                content={
                                    "detail": f"Daily training limit reached ({limits['daily']} for {tier} tier). Please try again tomorrow.",
                                    "limit_type": "daily",
                                    "limit": limits["daily"],
                                    "tier": tier,
                                },
                            )

                        if monthly_count >= limits["monthly"]:
                            return JSONResponse(
                                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                content={
                                    "detail": f"Monthly training limit reached ({limits['monthly']} for {tier} tier).",
                                    "limit_type": "monthly",
                                    "limit": limits["monthly"],
                                    "tier": tier,
                                },
                            )
                    except Exception as e:
                        logger.warning(f"Training quota check error: {e}")

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'"

        if "X-Request-ID" not in response.headers:
            import uuid
            response.headers["X-Request-ID"] = str(uuid.uuid4())

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        import uuid

        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        request.state.user_id = None

        start_time = time.time()

        logger.info(
            f"Request started: {request.method} {request.url.path}",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )

        response = await call_next(request)

        duration = time.time() - start_time
        status_code = response.status_code

        log_method = logger.info if status_code < 400 else logger.warning if status_code < 500 else logger.error
        log_method(
            f"Request completed: {request.method} {request.url.path} {status_code} {duration:.3f}s",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            duration=duration,
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.3f}s"

        return response


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    DANGEROUS_PATTERNS = [
        r"<script.*?>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"union\s+select",
        r"drop\s+table",
        r"insert\s+into",
        r"delete\s+from",
        r"--\s*$",
        r";\s*drop",
        r"'\s*or\s*'",
    ]

    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    body_str = body.decode("utf-8", errors="ignore")
                    for pattern in self.DANGEROUS_PATTERNS:
                        if re.search(pattern, body_str, re.IGNORECASE):
                            logger.warning(
                                "Potentially dangerous input detected",
                                path=request.url.path,
                                pattern=pattern,
                            )
                            return JSONResponse(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                content={"detail": "Invalid input detected"},
                            )
            except Exception:
                pass

        return await call_next(request)
