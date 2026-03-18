"""Retry decorator with exponential backoff for external API calls."""
import asyncio
import functools
import logging
from typing import Callable

logger = logging.getLogger(__name__)


def retry_async(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple = (Exception,),
):
    """Decorator for async functions with exponential backoff retry.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exceptions: Tuple of exception types to catch and retry
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}. "
                            f"Waiting {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries} retries failed for {func.__name__}: {e}"
                        )
            raise last_exception
        return wrapper
    return decorator


class LinkedInRateLimiter:
    """Track and respect LinkedIn API rate limits.

    LinkedIn allows ~100 API calls per day for most endpoints.
    """

    def __init__(self, redis_client=None, daily_limit: int = 100):
        self.redis = redis_client
        self.daily_limit = daily_limit

    async def check_and_increment(self, endpoint: str) -> bool:
        """Check if we can make a call and increment the counter.

        Returns True if the call is allowed, False if rate limited.
        """
        if not self.redis:
            return True

        import time
        day_key = f"linkedin_rate:{endpoint}:{int(time.time()) // 86400}"

        try:
            current = self.redis.incr(day_key)
            if current == 1:
                self.redis.expire(day_key, 86400)
            return current <= self.daily_limit
        except Exception:
            return True

    async def get_remaining(self, endpoint: str) -> int:
        """Get remaining API calls for today."""
        if not self.redis:
            return self.daily_limit

        import time
        day_key = f"linkedin_rate:{endpoint}:{int(time.time()) // 86400}"

        try:
            current = int(self.redis.get(day_key) or 0)
            return max(0, self.daily_limit - current)
        except Exception:
            return self.daily_limit
