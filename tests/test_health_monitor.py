"""Tests for HealthConfig, HealthMonitor, and _DomainHealth."""
import pytest
from scrapewarden.health_monitor import HealthConfig, HealthMonitor


# ---------------------------------------------------------------------------
# HealthConfig
# ---------------------------------------------------------------------------

class TestHealthConfig:
    def test_defaults(self):
        cfg = HealthConfig()
        assert cfg.window_size == 50
        assert cfg.min_health_score == 0.4
        assert cfg.response_time_threshold == 5.0

    def test_from_dict(self):
        cfg = HealthConfig.from_dict({"window_size": 20, "min_health_score": 0.6})
        assert cfg.window_size == 20
        assert cfg.min_health_score == 0.6
        assert cfg.response_time_threshold == 5.0  # default

    def test_from_dict_defaults(self):
        cfg = HealthConfig.from_dict({})
        assert cfg.window_size == 50


# ---------------------------------------------------------------------------
# HealthMonitor
# ---------------------------------------------------------------------------

@pytest.fixture
def monitor():
    return HealthMonitor(HealthConfig(window_size=10, min_health_score=0.5))


class TestHealthMonitor:
    def test_initial_health_score_is_one(self, monitor):
        assert monitor.health_score("example.com") == 1.0

    def test_is_healthy_with_no_data(self, monitor):
        assert monitor.is_healthy("example.com") is True

    def test_record_success_keeps_healthy(self, monitor):
        for _ in range(5):
            monitor.record("example.com", True, 0.1)
        assert monitor.is_healthy("example.com") is True
        assert monitor.health_score("example.com") == 1.0

    def test_record_failures_degrades_health(self, monitor):
        for _ in range(8):
            monitor.record("example.com", False, 0.5)
        for _ in range(2):
            monitor.record("example.com", True, 0.5)
        assert monitor.health_score("example.com") == pytest.approx(0.2)
        assert monitor.is_healthy("example.com") is False

    def test_avg_response_time(self, monitor):
        monitor.record("example.com", True, 1.0)
        monitor.record("example.com", True, 3.0)
        assert monitor.avg_response_time("example.com") == pytest.approx(2.0)

    def test_is_slow_below_threshold(self, monitor):
        monitor.record("example.com", True, 1.0)
        assert monitor.is_slow("example.com") is False

    def test_is_slow_above_threshold(self, monitor):
        for _ in range(5):
            monitor.record("example.com", True, 10.0)
        assert monitor.is_slow("example.com") is True

    def test_window_size_respected(self, monitor):
        # fill with failures then add successes beyond window
        for _ in range(10):
            monitor.record("example.com", False, 0.1)
        for _ in range(10):
            monitor.record("example.com", True, 0.1)
        # window is 10, all 10 slots should now be True
        assert monitor.health_score("example.com") == 1.0

    def test_domain_stats_keys(self, monitor):
        monitor.record("a.com", True, 0.2)
        stats = monitor.domain_stats("a.com")
        assert "health_score" in stats
        assert "avg_response_time" in stats
        assert "sample_count" in stats

    def test_all_stats_returns_all_domains(self, monitor):
        monitor.record("a.com", True, 0.1)
        monitor.record("b.com", False, 0.2)
        all_s = monitor.all_stats()
        assert "a.com" in all_s
        assert "b.com" in all_s
