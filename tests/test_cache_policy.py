"""Tests for CachePolicyConfig and CachePolicy."""
import time
import pytest
from scrapewarden.cache_policy import CachePolicy, CachePolicyConfig


class TestCachePolicyConfig:
    def test_defaults(self):
        cfg = CachePolicyConfig()
        assert cfg.enabled is True
        assert cfg.ttl_seconds == 300
        assert cfg.max_size == 1000
        assert "GET" in cfg.cacheable_methods
        assert 200 in cfg.cacheable_status_codes

    def test_from_dict(self):
        cfg = CachePolicyConfig.from_dict({"ttl_seconds": 60, "max_size": 50})
        assert cfg.ttl_seconds == 60
        assert cfg.max_size == 50

    def test_from_dict_defaults(self):
        cfg = CachePolicyConfig.from_dict({})
        assert cfg.enabled is True


class TestCachePolicy:
    @pytest.fixture
    def policy(self):
        return CachePolicy(CachePolicyConfig(ttl_seconds=10, max_size=5))

    def test_miss_on_empty(self, policy):
        assert policy.get("GET", "https://example.com") is None

    def test_put_and_get(self, policy):
        policy.put("GET", "https://example.com", 200, b"body", {})
        entry = policy.get("GET", "https://example.com")
        assert entry is not None
        assert entry.body == b"body"
        assert entry.status_code == 200

    def test_non_cacheable_method_not_stored(self, policy):
        policy.put("POST", "https://example.com", 200, b"body", {})
        assert policy.get("POST", "https://example.com") is None

    def test_non_cacheable_status_not_stored(self, policy):
        policy.put("GET", "https://example.com", 500, b"err", {})
        assert policy.get("GET", "https://example.com") is None

    def test_expired_entry_returns_none(self):
        policy = CachePolicy(CachePolicyConfig(ttl_seconds=0))
        policy.put("GET", "https://example.com", 200, b"x", {})
        time.sleep(0.01)
        assert policy.get("GET", "https://example.com") is None

    def test_max_size_evicts_oldest(self):
        policy = CachePolicy(CachePolicyConfig(max_size=2))
        policy.put("GET", "https://a.com", 200, b"a", {})
        policy.put("GET", "https://b.com", 200, b"b", {})
        policy.put("GET", "https://c.com", 200, b"c", {})
        assert policy.size() == 2

    def test_invalidate_removes_entry(self, policy):
        policy.put("GET", "https://example.com", 200, b"x", {})
        policy.invalidate("GET", "https://example.com")
        assert policy.get("GET", "https://example.com") is None

    def test_clear_empties_store(self, policy):
        policy.put("GET", "https://example.com", 200, b"x", {})
        policy.clear()
        assert policy.size() == 0

    def test_is_cacheable_request(self, policy):
        assert policy.is_cacheable_request("GET") is True
        assert policy.is_cacheable_request("POST") is False

    def test_is_cacheable_response(self, policy):
        assert policy.is_cacheable_response(200) is True
        assert policy.is_cacheable_response(404) is False
