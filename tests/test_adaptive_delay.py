"""Tests for the AdaptiveDelayManager."""

import time
import pytest
from scrapewarden.adaptive_delay import AdaptiveDelayConfig, AdaptiveDelayManager


class TestAdaptiveDelayConfig:
    def test_defaults(self):
        cfg = AdaptiveDelayConfig()
        assert cfg.initial_delay == 1.0
        assert cfg.min_delay == 0.5
        assert cfg.max_delay == 30.0
        assert cfg.increase_factor == 2.0
        assert cfg.decrease_factor == 0.9
        assert cfg.target_success_rate == 0.8

    def test_from_dict(self):
        cfg = AdaptiveDelayConfig.from_dict({
            "initial_delay": 2.0,
            "min_delay": 1.0,
            "max_delay": 60.0,
            "increase_factor": 3.0,
            "decrease_factor": 0.5,
            "target_success_rate": 0.9,
        })
        assert cfg.initial_delay == 2.0
        assert cfg.min_delay == 1.0
        assert cfg.max_delay == 60.0
        assert cfg.increase_factor == 3.0
        assert cfg.decrease_factor == 0.5
        assert cfg.target_success_rate == 0.9

    def test_from_dict_defaults(self):
        cfg = AdaptiveDelayConfig.from_dict({})
        assert cfg.initial_delay == 1.0
        assert cfg.min_delay == 0.5


class TestAdaptiveDelayManager:
    @pytest.fixture
    def manager(self):
        cfg = AdaptiveDelayConfig(
            initial_delay=1.0,
            min_delay=0.5,
            max_delay=16.0,
            increase_factor=2.0,
            decrease_factor=0.9,
            target_success_rate=0.8,
        )
        return AdaptiveDelayManager(cfg)

    def test_initial_delay(self, manager):
        assert manager.current_delay("example.com") == 1.0

    def test_delay_increases_on_failure(self, manager):
        manager.record_failure("example.com")
        assert manager.current_delay("example.com") == 2.0

    def test_delay_caps_at_max(self, manager):
        for _ in range(10):
            manager.record_failure("example.com")
        assert manager.current_delay("example.com") <= 16.0

    def test_delay_decreases_on_success(self, manager):
        # Push delay up first
        manager.record_failure("example.com")
        assert manager.current_delay("example.com") == 2.0
        manager.record_success("example.com")
        delay = manager.current_delay("example.com")
        assert delay < 2.0

    def test_delay_floors_at_min(self, manager):
        for _ in range(20):
            manager.record_success("example.com")
        assert manager.current_delay("example.com") >= 0.5

    def test_independent_domains(self, manager):
        manager.record_failure("example.com")
        assert manager.current_delay("example.com") == 2.0
        assert manager.current_delay("other.com") == 1.0

    def test_reset_domain(self, manager):
        manager.record_failure("example.com")
        manager.reset("example.com")
        assert manager.current_delay("example.com") == 1.0

    def test_multiple_failures_compound(self, manager):
        manager.record_failure("example.com")
        manager.record_failure("example.com")
        assert manager.current_delay("example.com") == 4.0
