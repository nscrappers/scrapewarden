"""Tests for BandwidthTracker and BandwidthMiddleware."""
import pytest

from scrapewarden.bandwidth_tracker import BandwidthConfig, BandwidthTracker
from scrapewarden.bandwidth_middleware import BandwidthMiddleware


# ---------------------------------------------------------------------------
# BandwidthConfig
# ---------------------------------------------------------------------------

class TestBandwidthConfig:
    def test_defaults(self):
        cfg = BandwidthConfig()
        assert cfg.max_bytes_per_domain is None
        assert cfg.warn_threshold_bytes is None

    def test_from_dict(self):
        cfg = BandwidthConfig.from_dict({"max_bytes_per_domain": 1024, "warn_threshold_bytes": 512})
        assert cfg.max_bytes_per_domain == 1024
        assert cfg.warn_threshold_bytes == 512

    def test_from_dict_defaults(self):
        cfg = BandwidthConfig.from_dict({})
        assert cfg.max_bytes_per_domain is None


# ---------------------------------------------------------------------------
# BandwidthTracker
# ---------------------------------------------------------------------------

@pytest.fixture
def tracker():
    return BandwidthTracker(BandwidthConfig(max_bytes_per_domain=200, warn_threshold_bytes=100))


class TestBandwidthTracker:
    def test_initial_stats_zero(self, tracker):
        s = tracker.stats("example.com")
        assert s["bytes_sent"] == 0
        assert s["bytes_received"] == 0
        assert s["total_bytes"] == 0

    def test_record_increments_counts(self, tracker):
        tracker.record("example.com", bytes_sent=50, bytes_received=80)
        s = tracker.stats("example.com")
        assert s["bytes_sent"] == 50
        assert s["bytes_received"] == 80
        assert s["total_bytes"] == 130
        assert s["request_count"] == 1

    def test_not_over_limit_initially(self, tracker):
        assert not tracker.is_over_limit("example.com")

    def test_over_limit_after_threshold(self, tracker):
        tracker.record("example.com", bytes_sent=100, bytes_received=101)
        assert tracker.is_over_limit("example.com")

    def test_near_limit_warn_threshold(self, tracker):
        tracker.record("example.com", bytes_sent=100)
        assert tracker.is_near_limit("example.com")

    def test_no_limit_never_over(self):
        t = BandwidthTracker()
        t.record("example.com", bytes_sent=10 ** 9)
        assert not t.is_over_limit("example.com")

    def test_reset_clears_domain(self, tracker):
        tracker.record("example.com", bytes_sent=50)
        tracker.reset("example.com")
        assert tracker.stats("example.com")["bytes_sent"] == 0

    def test_all_stats(self, tracker):
        tracker.record("a.com", bytes_sent=10)
        tracker.record("b.com", bytes_received=20)
        all_s = tracker.all_stats()
        assert "a.com" in all_s
        assert "b.com" in all_s


# ---------------------------------------------------------------------------
# BandwidthMiddleware
# ---------------------------------------------------------------------------

@pytest.fixture
def mw():
    return BandwidthMiddleware(BandwidthConfig(max_bytes_per_domain=500))


class TestBandwidthMiddleware:
    def test_on_request_allowed(self, mw):
        assert mw.on_request("https://example.com/page", body=b"hello") is True

    def test_on_request_blocked_over_limit(self, mw):
        mw.on_request("https://example.com/", body=b"x" * 300)
        mw.on_response("https://example.com/", body=b"y" * 210)
        result = mw.on_request("https://example.com/next", body=b"z")
        assert result is False
        assert mw.is_blocked("example.com")

    def test_from_dict(self):
        m = BandwidthMiddleware.from_dict({"max_bytes_per_domain": 1000})
        assert m is not None

    def test_reset_clears_block(self, mw):
        mw.on_request("https://example.com/", body=b"x" * 600)
        mw.reset("example.com")
        assert not mw.is_blocked("example.com")
        assert mw.on_request("https://example.com/", body=b"small") is True
