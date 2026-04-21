"""Tests for scrapewarden.retry_policy."""

import pytest

from scrapewarden.retry_policy import RetryPolicy, RetryPolicyConfig, RetryState


class TestRetryPolicy:
    def _policy(self, **kwargs) -> RetryPolicy:
        return RetryPolicy(RetryPolicyConfig(**kwargs))

    # --- should_retry ---

    def test_allows_retry_within_limit(self):
        policy = self._policy(max_retries=3)
        state = RetryState(attempts=2)
        assert policy.should_retry(state, status_code=500) is True

    def test_denies_retry_when_exhausted(self):
        policy = self._policy(max_retries=3)
        state = RetryState(attempts=3)
        assert policy.should_retry(state, status_code=500) is False

    def test_denies_retry_on_non_retryable_status(self):
        policy = self._policy(max_retries=5)
        state = RetryState(attempts=0)
        assert policy.should_retry(state, status_code=404) is False

    def test_allows_retry_when_status_none(self):
        policy = self._policy(max_retries=3)
        state = RetryState(attempts=1)
        assert policy.should_retry(state, status_code=None) is True

    def test_retries_on_429(self):
        policy = self._policy(max_retries=3)
        state = RetryState(attempts=0)
        assert policy.should_retry(state, status_code=429) is True

    # --- next_delay ---

    def test_delay_grows_with_attempts(self):
        policy = self._policy(base_delay=1.0, backoff_factor=2.0, jitter=False)
        d0 = policy.next_delay(RetryState(attempts=0))
        d1 = policy.next_delay(RetryState(attempts=1))
        d2 = policy.next_delay(RetryState(attempts=2))
        assert d0 < d1 < d2

    def test_delay_capped_at_max(self):
        policy = self._policy(base_delay=10.0, backoff_factor=10.0, max_delay=30.0, jitter=False)
        delay = policy.next_delay(RetryState(attempts=5))
        assert delay <= 30.0

    def test_jitter_produces_variation(self):
        policy = self._policy(base_delay=4.0, backoff_factor=2.0, jitter=True)
        state = RetryState(attempts=1)
        delays = {policy.next_delay(state) for _ in range(20)}
        assert len(delays) > 1, "Jitter should produce varied delays"

    # --- record_attempt ---

    def test_record_attempt_increments_counter(self):
        policy = self._policy(jitter=False)
        state = RetryState()
        policy.record_attempt(state, status_code=503)
        assert state.attempts == 1
        assert state.last_status == 503

    def test_record_attempt_accumulates_total_wait(self):
        policy = self._policy(base_delay=2.0, backoff_factor=1.0, jitter=False)
        state = RetryState()
        d1 = policy.record_attempt(state)
        d2 = policy.record_attempt(state)
        assert pytest.approx(state.total_wait) == d1 + d2

    def test_record_attempt_no_sleep_by_default(self, monkeypatch):
        slept = []
        monkeypatch.setattr("scrapewarden.retry_policy.time.sleep", slept.append)
        policy = self._policy()
        policy.record_attempt(RetryState())
        assert slept == []
