"""Tests for HealthMiddleware."""
import pytest
from scrapewarden.health_middleware import HealthMiddleware


@pytest.fixture
def mw():
    return HealthMiddleware.from_dict({"window_size": 10, "min_health_score": 0.5})


class TestHealthMiddlewareInit:
    def test_from_dict_creates_instance(self):
        m = HealthMiddleware.from_dict({"window_size": 20})
        assert m.monitor.config.window_size == 20

    def test_default_from_dict(self):
        m = HealthMiddleware.from_dict({})
        assert m.monitor.config.window_size == 50


class TestHealthMiddlewareBehavior:
    def test_on_response_success_recorded(self, mw):
        mw.on_request("req1", "example.com")
        mw.on_response("req1", "example.com", 200)
        assert mw.monitor.health_score("example.com") == 1.0

    def test_on_response_failure_recorded(self, mw):
        for i in range(10):
            mw.on_request(f"req{i}", "example.com")
            mw.on_response(f"req{i}", "example.com", 500)
        assert mw.monitor.health_score("example.com") == 0.0
        assert mw.is_healthy("example.com") is False

    def test_on_error_counts_as_failure(self, mw):
        for i in range(10):
            mw.on_request(f"req{i}", "example.com")
            mw.on_error(f"req{i}", "example.com")
        assert mw.monitor.health_score("example.com") == 0.0

    def test_on_response_explicit_success_flag(self, mw):
        mw.on_request("r1", "example.com")
        # status 500 but caller marks it success=True
        mw.on_response("r1", "example.com", 500, success=True)
        assert mw.monitor.health_score("example.com") == 1.0

    def test_elapsed_without_on_request_is_zero(self, mw):
        # Should not raise even if on_request was never called
        mw.on_response("missing", "example.com", 200)
        assert mw.monitor.avg_response_time("example.com") == pytest.approx(0.0)

    def test_stats_returns_all_domains(self, mw):
        mw.on_request("r1", "a.com")
        mw.on_response("r1", "a.com", 200)
        mw.on_request("r2", "b.com")
        mw.on_response("r2", "b.com", 404)
        s = mw.stats()
        assert "a.com" in s
        assert "b.com" in s
