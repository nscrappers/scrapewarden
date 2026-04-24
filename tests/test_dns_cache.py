"""Tests for scrapewarden.dns_cache."""
from __future__ import annotations

import socket
import time
from unittest.mock import patch

import pytest

from scrapewarden.dns_cache import DNSCache, DNSCacheConfig


class TestDNSCacheConfig:
    def test_defaults(self):
        cfg = DNSCacheConfig()
        assert cfg.ttl_seconds == 300.0
        assert cfg.max_entries == 1000
        assert cfg.fallback_on_error is True

    def test_from_dict(self):
        cfg = DNSCacheConfig.from_dict({"ttl_seconds": 60, "max_entries": 50, "fallback_on_error": False})
        assert cfg.ttl_seconds == 60.0
        assert cfg.max_entries == 50
        assert cfg.fallback_on_error is False

    def test_from_dict_defaults(self):
        cfg = DNSCacheConfig.from_dict({})
        assert cfg.ttl_seconds == 300.0
        assert cfg.max_entries == 1000


@pytest.fixture
def cache():
    return DNSCache(DNSCacheConfig(ttl_seconds=5.0, max_entries=5))


class TestDNSCache:
    def test_resolve_returns_address(self, cache):
        with patch("socket.gethostbyname", return_value="93.184.216.34"):
            addr = cache.resolve("example.com")
        assert addr == "93.184.216.34"

    def test_cached_result_not_re_resolved(self, cache):
        with patch("socket.gethostbyname", return_value="1.2.3.4") as mock_dns:
            cache.resolve("example.com")
            cache.resolve("example.com")
        assert mock_dns.call_count == 1

    def test_expired_entry_re_resolved(self, cache):
        with patch("socket.gethostbyname", return_value="1.2.3.4"):
            cache.resolve("example.com")
        # Manually expire the entry
        cache._cache["example.com"].expires_at = time.monotonic() - 1
        with patch("socket.gethostbyname", return_value="5.6.7.8") as mock_dns:
            addr = cache.resolve("example.com")
        assert addr == "5.6.7.8"
        assert mock_dns.call_count == 1

    def test_invalidate_removes_entry(self, cache):
        with patch("socket.gethostbyname", return_value="1.2.3.4"):
            cache.resolve("example.com")
        cache.invalidate("example.com")
        assert "example.com" not in cache._cache

    def test_clear_empties_cache(self, cache):
        with patch("socket.gethostbyname", return_value="1.2.3.4"):
            cache.resolve("example.com")
            cache.resolve("other.com")
        cache.clear()
        assert cache.size == 0

    def test_fallback_on_error_uses_stale(self, cache):
        with patch("socket.gethostbyname", return_value="1.2.3.4"):
            cache.resolve("example.com")
        cache._cache["example.com"].expires_at = time.monotonic() - 1
        with patch("socket.gethostbyname", side_effect=socket.gaierror):
            addr = cache.resolve("example.com")
        assert addr == "1.2.3.4"

    def test_no_fallback_raises_on_error(self):
        cfg = DNSCacheConfig(fallback_on_error=False)
        c = DNSCache(cfg)
        with patch("socket.gethostbyname", side_effect=socket.gaierror):
            with pytest.raises(socket.gaierror):
                c.resolve("bad.invalid")

    def test_evicts_when_max_entries_reached(self):
        cfg = DNSCacheConfig(max_entries=3, ttl_seconds=60)
        c = DNSCache(cfg)
        hosts = ["a.com", "b.com", "c.com", "d.com"]
        with patch("socket.gethostbyname", side_effect=lambda h: "1.1.1.1"):
            for h in hosts:
                c.resolve(h)
        assert c.size <= 3

    def test_cached_hostnames(self, cache):
        with patch("socket.gethostbyname", return_value="1.2.3.4"):
            cache.resolve("alpha.com")
            cache.resolve("beta.com")
        assert set(cache.cached_hostnames()) == {"alpha.com", "beta.com"}
