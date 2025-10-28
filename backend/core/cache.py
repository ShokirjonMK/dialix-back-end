"""
Redis Caching Layer for Performance Optimization
"""

import json
import logging
import hashlib
from typing import Any, Optional, Callable
from functools import wraps

import redis
from backend.core import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Redis caching manager"""

    def __init__(self):
        try:
            self.client = redis.from_url(
                settings.REDIS_URL, decode_responses=True, health_check_interval=30
            )
            # Test connection
            self.client.ping()
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.client = None

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.client:
            return None

        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Cache get error: {e}")

        return None

    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value to cache"""
        if not self.client:
            return False

        try:
            ttl = ttl or settings.REDIS_CACHE_TTL
            serialized = json.dumps(value, default=str)
            self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete from cache"""
        if not self.client:
            return False

        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    def delete_pattern(self, pattern: str) -> bool:
        """Delete all keys matching pattern"""
        if not self.client:
            return False

        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.client:
            return False

        try:
            return self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False

    def get_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        # Create a deterministic hash from arguments
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        hash_obj = hashlib.md5(key_data.encode())
        return f"cache:{hash_obj.hexdigest()}"


# Global cache instance
cache_manager = CacheManager()


def cached(ttl: int = None, key_prefix: str = None):
    """
    Decorator to cache function results

    Usage:
        @cached(ttl=300, key_prefix="records")
        def get_records(owner_id: str):
            # Expensive query
            pass
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            prefix = key_prefix or func.__name__
            cache_key = cache_manager.get_cache_key(prefix, *args, **kwargs)

            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.info(f"Cache HIT for {cache_key}")
                return cached_result

            # Execute function and cache result
            logger.info(f"Cache MISS for {cache_key}")
            result = func(*args, **kwargs)

            # Cache the result (handle both async and sync)
            if hasattr(result, "__await__"):
                result = await result

            cache_manager.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator


def invalidate_cache(pattern: str):
    """Invalidate cache by pattern"""
    cache_manager.delete_pattern(pattern)
