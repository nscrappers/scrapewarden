"""Tests for BackoffStrategy."""
import pytest

from scrapewarden.backoff_strategy import (
    BackoffConfig,
    BackoffStrategy,
    BackoffType,
)


class TestBackoffConfig:
    def test_defaults(self):
        cfg = BackoffConfig()
        assert cfg.strategy == BackoffType.EXPONENTIAL
        assert cfg.base_delay == 1.0
        assert cfg.max_delay == 60.0
        assert cfg.multiplier == 2.0

    def test_from_dict(self):
        cfg = BackoffConfig.from_dict(
            {"strategy": "linear", "base_delay": 2.0, "max_delay": 30.0}
        )
        assert cfg.strategy == BackoffType.LINEAR
        assert cfg.base_delay == 2.0
        assert cfg.max_delay == 30.0

    def test_from_dict_defaults(self):
        cfg = BackoffConfig.from_dict({})
        assert cfg.strategy == BackoffType.EXPONENTIAL


class TestBackoffStrategy:
    @pytest.fixture
    def exp_strategy(self):
        cfg = BackoffConfig(strategy=BackoffType.EXPONENTIAL, base_delay=1.0, multiplier=2.0, max_delay=60.0)
        return BackoffStrategy(cfg)

    def test_exponential_first_attempt(self, exp_strategy):
        assert exp_strategy.delay_for(0) == pytest.approx(1.0)

    def test_exponential_second_attempt(self, exp_strategy):
        assert exp_strategy.delay_for(1) == pytest.approx(2.0)

    def test_exponential_third_attempt(self, exp_strategy):
        assert exp_strategy.delay_for(2) == pytest.approx(4.0)

    def test_max_delay_capped(self):
        cfg = BackoffConfig(strategy=BackoffType.EXPONENTIAL, base_delay=1.0, multiplier=2.0, max_delay=5.0)
        strategy = BackoffStrategy(cfg)
        assert strategy.delay_for(10) == pytest.approx(5.0)

    def test_fixed_strategy(self):
        cfg = BackoffConfig(strategy=BackoffType.FIXED, base_delay=3.0, max_delay=60.0)
        strategy = BackoffStrategy(cfg)
        assert strategy.delay_for(0) == pytest.approx(3.0)
        assert strategy.delay_for(5) == pytest.approx(3.0)

    def test_linear_strategy(self):
        cfg = BackoffConfig(strategy=BackoffType.LINEAR, base_delay=2.0, max_delay=60.0)
        strategy = BackoffStrategy(cfg)
        assert strategy.delay_for(0) == pytest.approx(2.0)
        assert strategy.delay_for(2) == pytest.approx(6.0)

    def test_jittered_within_bounds(self):
        cfg = BackoffConfig(strategy=BackoffType.JITTERED, base_delay=1.0, multiplier=2.0, max_delay=60.0, jitter_range=0.5)
        strategy = BackoffStrategy(cfg)
        for attempt in range(5):
            delay = strategy.delay_for(attempt)
            assert delay >= 0.0
            assert delay <= cfg.max_delay

    def test_delays_list_length(self, exp_strategy):
        delays = exp_strategy.delays(4)
        assert len(delays) == 4

    def test_delays_list_increasing(self, exp_strategy):
        delays = exp_strategy.delays(5)
        for i in range(len(delays) - 1):
            assert delays[i] <= delays[i + 1]

    def test_default_config(self):
        strategy = BackoffStrategy()
        assert strategy.delay_for(0) >= 0.0
