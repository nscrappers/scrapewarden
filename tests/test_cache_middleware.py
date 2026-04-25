"""Tests for CacheMiddleware."""
import pytest
from scrapewarden.cache_middleware import CacheMiddleware
from scrapewarden.cache_policy import CachePolicyConfig


@pytest.fixture
def middleware():
    return CacheMiddleware(CachePolicyConfig(ttl_seconds=60, max_size=100))


class TestCacheMiddlewareInit:
    def test_from_dict_creates_instance(self):
        m = CacheMiddleware.from_dict({"ttl_seconds": 30})
        assert isinstance(m, CacheMiddleware)

    def test_default_from_dict(self):
        m = CacheMiddleware.from_dict({})
        assert m.hits == 0 and m.misses == 0


class TestCacheMiddlewareBehavior:
    def test_cache_miss_increments_misses(self, middleware):
        result = middleware.on_request("GET", "https://example.com")
        assert result is None
        assert middleware.misses == 1

    def test_cache_hit_after_response(self, middleware):
        middleware.on_response("GET", "https://example.com", 200, b"hello", {})
        entry = middleware.on_request("GET", "https://example.com")
        assert entry is not None
        assert entry.body == b"hello"
        assert middleware.hits == 1

    def test_post_request_not_cached(self, middleware):
        middleware.on_response("POST", "https://example.com", 200, b"data", {})
        result = middleware.on_request("POST", "https://example.com")
        assert result is None

    def test_hit_rate_calculation(self, middleware):
        middleware.on_response("GET", "https://example.com", 200, b"x", {})
        middleware.on_request("GET", "https://example.com")  # hit
        middleware.on_request("GET", "https://other.com")   # miss
        assert middleware.hit_rate == pytest.approx(0.5)

    def test_hit_rate_zero_when_no_requests(self, middleware):
        assert middleware.hit_rate == 0.0

    def test_invalidate_clears_entry(self, middleware):
        middleware.on_response("GET", "https://example.com", 200, b"x", {})
        middleware.invalidate("GET", "https://example.com")
        result = middleware.on_request("GET", "https://example.com")
        assert result is None

    def test_clear_resets_stats(self, middleware):
        middleware.on_response("GET", "https://example.com", 200, b"x", {})
        middleware.on_request("GET", "https://example.com")
        middleware.clear()
        assert middleware.hits == 0
        assert middleware.misses == 0

    def test_stats_dict_keys(self, middleware):
        s = middleware.stats()
        assert "hits" in s
        assert "misses" in s
        assert "hit_rate" in s
        assert "cache_size" in s

    def test_stats_cache_size_reflects_entries(self, middleware):
        middleware.on_response("GET", "https://a.com", 200, b"a", {})
        middleware.on_response("GET", "https://b.com", 200, b"b", {})
        assert middleware.stats()["cache_size"] == 2
