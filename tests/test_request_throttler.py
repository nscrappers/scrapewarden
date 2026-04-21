"""Tests for domain-level request throttling."""

import time
import pytest
from scrapewarden.request_throttler import ThrottleConfig, RequestThrottler


class TestThrottleConfig:
    def test_defaults(self):
        cfg = ThrottleConfig()
        assert cfg.default_delay == 1.0
        assert cfg.jitter == 0.0
        assert cfg.per_domain_delays == {}

    def test_from_dict(self):
        cfg = ThrottleConfig.from_dict(
            {"default_delay": 2.5, "per_domain_delays": {"example.com": 0.5}, "jitter": 0.1}
        )
        assert cfg.default_delay == 2.5
        assert cfg.per_domain_delays["example.com"] == 0.5
        assert cfg.jitter == 0.1


class TestRequestThrottler:
    @pytest.fixture
    def throttler(self):
        cfg = ThrottleConfig(default_delay=0.05)
        return RequestThrottler(config=cfg)

    def test_first_request_no_wait(self, throttler):
        waited = throttler.wait_if_needed("example.com")
        assert waited == 0.0

    def test_second_request_waits(self, throttler):
        throttler.wait_if_needed("example.com")
        waited = throttler.wait_if_needed("example.com")
        assert waited > 0.0

    def test_different_domains_independent(self, throttler):
        throttler.wait_if_needed("a.com")
        waited = throttler.wait_if_needed("b.com")
        assert waited == 0.0

    def test_delay_elapses_naturally(self, throttler):
        throttler.wait_if_needed("example.com")
        time.sleep(0.06)
        waited = throttler.wait_if_needed("example.com")
        assert waited == 0.0

    def test_per_domain_delay_override(self):
        cfg = ThrottleConfig(default_delay=1.0, per_domain_delays={"fast.com": 0.02})
        t = RequestThrottler(config=cfg)
        t.wait_if_needed("fast.com")
        start = time.monotonic()
        t.wait_if_needed("fast.com")
        elapsed = time.monotonic() - start
        assert elapsed < 0.5  # used per-domain delay, not default 1.0s

    def test_time_until_ready_zero_on_first(self, throttler):
        assert throttler.time_until_ready("new.com") == 0.0

    def test_time_until_ready_positive_after_request(self, throttler):
        throttler.wait_if_needed("example.com")
        remaining = throttler.time_until_ready("example.com")
        assert remaining > 0.0

    def test_reset_single_domain(self, throttler):
        throttler.wait_if_needed("example.com")
        throttler.reset("example.com")
        assert throttler.time_until_ready("example.com") == 0.0

    def test_reset_all_domains(self, throttler):
        throttler.wait_if_needed("a.com")
        throttler.wait_if_needed("b.com")
        throttler.reset()
        assert throttler.time_until_ready("a.com") == 0.0
        assert throttler.time_until_ready("b.com") == 0.0

    def test_max_delay_cap(self):
        cfg = ThrottleConfig(
            default_delay=1.0,
            max_delay=0.03,
            per_domain_delays={"slow.com": 999.0},
        )
        t = RequestThrottler(config=cfg)
        t.wait_if_needed("slow.com")
        start = time.monotonic()
        t.wait_if_needed("slow.com")
        elapsed = time.monotonic() - start
        assert elapsed < 1.0  # capped at max_delay=0.03
