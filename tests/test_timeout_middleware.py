"""Tests for TimeoutMiddleware."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from scrapewarden.timeout_middleware import TimeoutMiddleware
from scrapewarden.timeout_manager import TimeoutConfig


@pytest.fixture
def middleware():
    return TimeoutMiddleware.from_dict({
        "default_timeout": 10.0,
        "connect_timeout": 5.0,
        "read_timeout": 8.0,
        "per_domain": {
            "slow.example.com": {"default_timeout": 30.0}
        }
    })


class TestTimeoutMiddlewareInit:
    def test_from_dict_creates_instance(self, middleware):
        assert middleware is not None

    def test_default_from_dict(self):
        mw = TimeoutMiddleware.from_dict({})
        assert mw is not None

    def test_get_timeouts_returns_dict(self, middleware):
        timeouts = middleware.get_timeouts("https://example.com/page")
        assert isinstance(timeouts, dict)

    def test_get_timeouts_contains_expected_keys(self, middleware):
        timeouts = middleware.get_timeouts("https://example.com/page")
        assert "connect" in timeouts or "total" in timeouts or "read" in timeouts

    def test_get_timeouts_default_values(self, middleware):
        timeouts = middleware.get_timeouts("https://example.com/page")
        # Should reflect configured default_timeout or connect_timeout
        assert any(v > 0 for v in timeouts.values())


class TestTimeoutMiddlewarePerDomain:
    def test_per_domain_timeout_applied(self, middleware):
        slow_timeouts = middleware.get_timeouts("https://slow.example.com/data")
        default_timeouts = middleware.get_timeouts("https://fast.example.com/data")
        # slow domain has a higher configured timeout
        slow_total = slow_timeouts.get("total") or slow_timeouts.get("read") or 0
        default_total = default_timeouts.get("total") or default_timeouts.get("read") or 0
        assert slow_total >= default_total

    def test_unknown_domain_uses_defaults(self, middleware):
        timeouts = middleware.get_timeouts("https://unknown.org/path")
        assert timeouts is not None
        assert len(timeouts) > 0


class TestTimeoutMiddlewareOnTimeout:
    def test_on_timeout_returns_domain(self, middleware):
        result = middleware.on_timeout("https://example.com/page")
        assert result is not None

    def test_on_timeout_increments_count(self, middleware):
        url = "https://example.com/page"
        before = middleware._timeout_counts.get("example.com", 0)
        middleware.on_timeout(url)
        after = middleware._timeout_counts.get("example.com", 0)
        assert after == before + 1

    def test_on_timeout_multiple_domains_tracked_separately(self, middleware):
        middleware.on_timeout("https://alpha.com/a")
        middleware.on_timeout("https://alpha.com/b")
        middleware.on_timeout("https://beta.com/x")
        assert middleware._timeout_counts.get("alpha.com", 0) == 2
        assert middleware._timeout_counts.get("beta.com", 0) == 1


class TestTimeoutMiddlewareOnRequest:
    def test_on_request_returns_timeouts(self, middleware):
        result = middleware.on_request("https://example.com/page")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_on_request_slow_domain(self, middleware):
        result = middleware.on_request("https://slow.example.com/resource")
        assert isinstance(result, dict)

    def test_on_request_does_not_raise(self, middleware):
        try:
            middleware.on_request("https://example.com/safe")
        except Exception as exc:
            pytest.fail(f"on_request raised unexpectedly: {exc}")
