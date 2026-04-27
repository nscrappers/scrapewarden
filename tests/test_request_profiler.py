"""Tests for RequestProfiler and ProfilerMiddleware."""
import pytest

from scrapewarden.request_profiler import ProfilerConfig, RequestProfiler
from scrapewarden.profiler_middleware import ProfilerMiddleware


# ---------------------------------------------------------------------------
# ProfilerConfig
# ---------------------------------------------------------------------------

class TestProfilerConfig:
    def test_defaults(self):
        cfg = ProfilerConfig()
        assert cfg.enabled is True
        assert cfg.window_size == 100
        assert cfg.slow_threshold_seconds == 3.0

    def test_from_dict(self):
        cfg = ProfilerConfig.from_dict({"window_size": 50, "slow_threshold_seconds": 1.5})
        assert cfg.window_size == 50
        assert cfg.slow_threshold_seconds == 1.5

    def test_from_dict_defaults(self):
        cfg = ProfilerConfig.from_dict({})
        assert cfg.enabled is True


# ---------------------------------------------------------------------------
# RequestProfiler
# ---------------------------------------------------------------------------

@pytest.fixture
def profiler():
    return RequestProfiler(ProfilerConfig(window_size=10, slow_threshold_seconds=2.0))


class TestRequestProfiler:
    def test_empty_profile_returns_empty_dict(self, profiler):
        assert profiler.profile("example.com") == {}

    def test_record_and_profile(self, profiler):
        profiler.record("example.com", elapsed=0.5, req_bytes=100, resp_bytes=200, status=200)
        p = profiler.profile("example.com")
        assert p["sample_count"] == 1
        assert p["avg_elapsed_seconds"] == pytest.approx(0.5, abs=1e-4)
        assert p["total_request_bytes"] == 100
        assert p["total_response_bytes"] == 200

    def test_slow_request_rate(self, profiler):
        profiler.record("slow.com", elapsed=3.5, req_bytes=0, resp_bytes=0, status=200)
        profiler.record("slow.com", elapsed=0.1, req_bytes=0, resp_bytes=0, status=200)
        p = profiler.profile("slow.com")
        assert p["slow_request_rate"] == pytest.approx(0.5, abs=1e-4)

    def test_slow_domains_returned(self, profiler):
        profiler.record("fast.com", elapsed=0.1, req_bytes=0, resp_bytes=0, status=200)
        profiler.record("slow.com", elapsed=5.0, req_bytes=0, resp_bytes=0, status=200)
        slow = profiler.slow_domains()
        assert "slow.com" in slow
        assert "fast.com" not in slow

    def test_disabled_profiler_records_nothing(self):
        p = RequestProfiler(ProfilerConfig(enabled=False))
        p.record("example.com", elapsed=1.0, req_bytes=50, resp_bytes=50, status=200)
        assert p.profile("example.com") == {}

    def test_window_evicts_old_samples(self):
        p = RequestProfiler(ProfilerConfig(window_size=3))
        for _ in range(5):
            p.record("x.com", elapsed=1.0, req_bytes=10, resp_bytes=10, status=200)
        assert p.profile("x.com")["sample_count"] == 3


# ---------------------------------------------------------------------------
# ProfilerMiddleware
# ---------------------------------------------------------------------------

@pytest.fixture
def mw():
    return ProfilerMiddleware.from_dict({"window_size": 20, "slow_threshold_seconds": 2.0})


class TestProfilerMiddleware:
    def test_from_dict_creates_instance(self):
        m = ProfilerMiddleware.from_dict({})
        assert isinstance(m, ProfilerMiddleware)

    def test_on_request_then_response_records_profile(self, mw):
        mw.on_request("req-1", "https://example.com/page", body=b"hello")
        mw.on_response("req-1", "https://example.com/page", 200, b"world", b"hello")
        p = mw.profile("https://example.com/page")
        assert p["sample_count"] == 1
        assert p["total_request_bytes"] == 5
        assert p["total_response_bytes"] == 5

    def test_missing_start_does_not_raise(self, mw):
        # on_response without on_request should be a no-op
        mw.on_response("orphan", "https://x.com", 200, b"data")
        assert mw.profile("x.com") == {}

    def test_all_profiles_aggregates_domains(self, mw):
        mw.on_request("r1", "https://a.com/")
        mw.on_response("r1", "https://a.com/", 200, b"aa")
        mw.on_request("r2", "https://b.com/")
        mw.on_response("r2", "https://b.com/", 404, b"bb")
        profiles = mw.all_profiles()
        assert "a.com" in profiles
        assert "b.com" in profiles
