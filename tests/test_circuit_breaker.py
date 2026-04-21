import time
import pytest
from scrapewarden.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState


class TestCircuitBreaker:
    def _breaker(self, failure_threshold=3, recovery_timeout=30.0, success_threshold=2):
        config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold,
        )
        return CircuitBreaker(config=config)

    def test_initial_state_is_closed(self):
        cb = self._breaker()
        assert cb.state == CircuitState.CLOSED

    def test_allows_requests_when_closed(self):
        cb = self._breaker()
        assert cb.allow_request() is True

    def test_opens_after_failure_threshold(self):
        cb = self._breaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_blocks_requests_when_open(self):
        cb = self._breaker(failure_threshold=1)
        cb.record_failure()
        assert cb.allow_request() is False

    def test_transitions_to_half_open_after_timeout(self):
        cb = self._breaker(failure_threshold=1, recovery_timeout=0.05)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.1)
        assert cb.state == CircuitState.HALF_OPEN

    def test_allows_request_in_half_open(self):
        cb = self._breaker(failure_threshold=1, recovery_timeout=0.05)
        cb.record_failure()
        time.sleep(0.1)
        assert cb.allow_request() is True

    def test_closes_after_success_threshold_in_half_open(self):
        cb = self._breaker(failure_threshold=1, recovery_timeout=0.05, success_threshold=2)
        cb.record_failure()
        time.sleep(0.1)
        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_reopens_on_failure_in_half_open(self):
        cb = self._breaker(failure_threshold=1, recovery_timeout=0.05)
        cb.record_failure()
        time.sleep(0.1)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_failure_count_in_closed(self):
        cb = self._breaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        cb.record_failure()
        # Only 2 failures after reset, should still be closed
        assert cb.state == CircuitState.CLOSED

    def test_manual_reset(self):
        cb = self._breaker(failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True
