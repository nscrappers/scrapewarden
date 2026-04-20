"""Tests for the token bucket rate limiter."""

import time
import threading
import pytest
from scrapewarden.rate_limiter import RateLimiter, RateLimiterConfig, TokenBucket


class TestTokenBucket:
    def test_immediate_consume_within_capacity(self):
        bucket = TokenBucket(rate=10.0, capacity=5)
        wait = bucket.consume(1)
        assert wait == 0.0

    def test_consume_returns_wait_when_empty(self):
        bucket = TokenBucket(rate=1.0, capacity=1)
        bucket.consume(1)  # drain
        wait = bucket.consume(1)
        assert wait > 0.0
        assert wait <= 1.1  # roughly 1 second

    def test_burst_capacity_respected(self):
        bucket = TokenBucket(rate=1.0, capacity=3)
        for _ in range(3):
            assert bucket.consume() == 0.0
        assert bucket.consume() > 0.0

    def test_refill_over_time(self):
        bucket = TokenBucket(rate=10.0, capacity=10)
        for _ in range(10):
            bucket.consume()
        time.sleep(0.2)
        wait = bucket.consume()
        assert wait == 0.0  # should have refilled ~2 tokens


class TestRateLimiter:
    def test_default_config(self):
        config = RateLimiterConfig(requests_per_second=100.0, burst_size=10)
        limiter = RateLimiter(config)
        wait = limiter.wait_for_slot("example.com")
        assert wait == 0.0

    def test_domain_override(self):
        config = RateLimiterConfig(
            requests_per_second=1.0,
            burst_size=1,
            domain_overrides={"fast.com": {"requests_per_second": 100.0, "burst_size": 10}},
        )
        limiter = RateLimiter(config)
        for _ in range(5):
            wait = limiter.wait_for_slot("fast.com")
            assert wait == 0.0

    def test_separate_buckets_per_domain(self):
        config = RateLimiterConfig(requests_per_second=100.0, burst_size=2)
        limiter = RateLimiter(config)
        limiter.wait_for_slot("a.com")
        limiter.wait_for_slot("a.com")
        # b.com bucket should still be full
        wait = limiter.wait_for_slot("b.com")
        assert wait == 0.0

    def test_get_stats(self):
        config = RateLimiterConfig(requests_per_second=10.0, burst_size=5)
        limiter = RateLimiter(config)
        limiter.wait_for_slot("stats.com")
        stats = limiter.get_stats()
        assert "stats.com" in stats
        assert "tokens" in stats["stats.com"]

    def test_thread_safety(self):
        config = RateLimiterConfig(requests_per_second=1000.0, burst_size=100)
        limiter = RateLimiter(config)
        results = []

        def make_request():
            wait = limiter.wait_for_slot("concurrent.com")
            results.append(wait)

        threads = [threading.Thread(target=make_request) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 20
