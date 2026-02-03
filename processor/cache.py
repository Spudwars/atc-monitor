"""
Simple in-memory caching for ATC Monitor.

Provides TTL-based caching for expensive operations like
callsign lookups and repeated queries.
"""

import time
import threading
from dataclasses import dataclass
from typing import Any, Optional, Callable, TypeVar

T = TypeVar('T')


@dataclass
class CacheEntry:
    """A cached value with expiration time."""
    value: Any
    expires_at: float


class Cache:
    """
    Thread-safe in-memory cache with TTL support.

    Usage:
        cache = Cache(default_ttl=300)  # 5 minute default
        cache.set("key", value)
        value = cache.get("key")

        # Or with decorator:
        @cache.cached("prefix", ttl=60)
        def expensive_function(arg):
            ...
    """

    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        Initialize cache.

        Args:
            default_ttl: Default time-to-live in seconds
            max_size: Maximum number of entries before eviction
        """
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            if time.time() > entry.expires_at:
                del self._cache[key]
                self._misses += 1
                return None

            self._hits += 1
            return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        if ttl is None:
            ttl = self._default_ttl

        with self._lock:
            # Evict if at max size
            if len(self._cache) >= self._max_size:
                self._evict_expired()
                if len(self._cache) >= self._max_size:
                    self._evict_oldest()

            self._cache[key] = CacheEntry(
                value=value,
                expires_at=time.time() + ttl
            )

    def delete(self, key: str) -> bool:
        """
        Delete a key from cache.

        Returns True if key existed.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()

    def invalidate_prefix(self, prefix: str) -> int:
        """
        Invalidate all keys starting with prefix.

        Returns number of keys invalidated.
        """
        with self._lock:
            keys_to_delete = [
                k for k in self._cache.keys()
                if k.startswith(prefix)
            ]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)

    def stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                'size': len(self._cache),
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': self._hits / total if total > 0 else 0,
            }

    def cached(
        self,
        prefix: str,
        ttl: Optional[int] = None
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        Decorator for caching function results.

        Args:
            prefix: Key prefix for this function's cache entries
            ttl: Time-to-live in seconds

        Usage:
            @cache.cached("user", ttl=60)
            def get_user(user_id: int) -> User:
                ...
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            def wrapper(*args, **kwargs) -> T:
                # Build cache key from prefix and arguments
                key_parts = [prefix]
                key_parts.extend(str(a) for a in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                key = ':'.join(key_parts)

                # Try cache first
                cached_value = self.get(key)
                if cached_value is not None:
                    return cached_value

                # Compute and cache
                result = func(*args, **kwargs)
                self.set(key, result, ttl)
                return result

            return wrapper
        return decorator

    def _evict_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        now = time.time()
        expired = [
            k for k, v in self._cache.items()
            if now > v.expires_at
        ]
        for key in expired:
            del self._cache[key]
        return len(expired)

    def _evict_oldest(self) -> None:
        """Evict the oldest 10% of entries."""
        if not self._cache:
            return

        # Sort by expiration time and remove oldest
        sorted_keys = sorted(
            self._cache.keys(),
            key=lambda k: self._cache[k].expires_at
        )
        evict_count = max(1, len(sorted_keys) // 10)
        for key in sorted_keys[:evict_count]:
            del self._cache[key]


# Global cache instance
_global_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """Get or create the global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = Cache()
    return _global_cache


def set_cache(cache: Cache) -> None:
    """Set the global cache instance (useful for testing)."""
    global _global_cache
    _global_cache = cache
