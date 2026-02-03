"""Tests for caching module."""

import time
import pytest
from processor.cache import Cache, get_cache


class TestCacheBasics:
    """Test basic cache operations."""

    def test_set_and_get(self):
        cache = Cache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_key(self):
        cache = Cache()
        assert cache.get("nonexistent") is None

    def test_delete(self):
        cache = Cache()
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_delete_missing(self):
        cache = Cache()
        assert cache.delete("nonexistent") is False

    def test_clear(self):
        cache = Cache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestCacheTTL:
    """Test TTL (time-to-live) functionality."""

    def test_expired_entry_returns_none(self):
        cache = Cache(default_ttl=1)
        cache.set("key1", "value1", ttl=0)  # Immediate expiry
        time.sleep(0.01)
        assert cache.get("key1") is None

    def test_custom_ttl(self):
        cache = Cache(default_ttl=1)
        cache.set("key1", "value1", ttl=3600)  # 1 hour
        assert cache.get("key1") == "value1"


class TestCacheStats:
    """Test cache statistics."""

    def test_stats_hits(self):
        cache = Cache()
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("key1")

        stats = cache.stats()
        assert stats['hits'] == 2
        assert stats['misses'] == 0

    def test_stats_misses(self):
        cache = Cache()
        cache.get("nonexistent")
        cache.get("also_nonexistent")

        stats = cache.stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 2

    def test_hit_rate(self):
        cache = Cache()
        cache.set("key1", "value1")
        cache.get("key1")  # hit
        cache.get("key2")  # miss

        stats = cache.stats()
        assert stats['hit_rate'] == 0.5


class TestCacheInvalidation:
    """Test cache invalidation."""

    def test_invalidate_prefix(self):
        cache = Cache()
        cache.set("user:1", "alice")
        cache.set("user:2", "bob")
        cache.set("post:1", "hello")

        count = cache.invalidate_prefix("user:")
        assert count == 2
        assert cache.get("user:1") is None
        assert cache.get("user:2") is None
        assert cache.get("post:1") == "hello"


class TestCachedDecorator:
    """Test the @cached decorator."""

    def test_cached_function(self):
        cache = Cache()
        call_count = 0

        @cache.cached("test")
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_function(5)
        result2 = expensive_function(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 1  # Only called once

    def test_cached_function_different_args(self):
        cache = Cache()
        call_count = 0

        @cache.cached("test")
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        expensive_function(5)
        expensive_function(10)

        assert call_count == 2  # Called for each unique arg


class TestCacheEviction:
    """Test cache size limits and eviction."""

    def test_max_size_eviction(self):
        cache = Cache(max_size=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # Should trigger eviction

        stats = cache.stats()
        assert stats['size'] <= 3
