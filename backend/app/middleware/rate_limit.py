"""Rate limiting middleware using Redis."""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

import redis

from app.config import get_settings

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple sliding window rate limiter backed by Redis.

    Limits requests per IP per minute.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.rpm = requests_per_minute
        try:
            self.redis = redis.from_url(settings.redis_url, decode_responses=True)
        except Exception:
            self.redis = None

    async def dispatch(self, request: Request, call_next):
        if not self.redis:
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path == "/api/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}:{int(time.time()) // 60}"

        try:
            current = self.redis.incr(key)
            if current == 1:
                self.redis.expire(key, 60)

            if current > self.rpm:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please slow down."},
                )
        except Exception:
            # If Redis is down, allow the request through
            pass

        response = await call_next(request)
        return response
