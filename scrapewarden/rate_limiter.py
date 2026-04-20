"""Token bucket rate limiter for controlling request throughput."""

import time
import threading
from dataclasses import dataclass, field


@dataclass
class RateLimiterConfig:
    requests_per_second: float = 1.0
    burst_size: int = 5
    domain_overrides: dict = field(default_factory=dict)


class TokenBucket:
    """Thread-safe token bucket implementation."""

    def __init__(self, rate: float, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last_refill = now

    def consume(self, tokens: int = 1) -> float:
        """Try to consume tokens. Returns wait time in seconds (0 if immediate)."""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return 0.0
            deficit = tokens - self._tokens
            wait_time = deficit / self.rate
            return wait_time


class RateLimiter:
    """Per-domain rate limiter using token buckets."""

    def __init__(self, config: RateLimiterConfig):
        self.config = config
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

    def _get_bucket(self, domain: str) -> TokenBucket:
        with self._lock:
            if domain not in self._buckets:
                override = self.config.domain_overrides.get(domain, {})
                rate = override.get("requests_per_second", self.config.requests_per_second)
                burst = override.get("burst_size", self.config.burst_size)
                self._buckets[domain] = TokenBucket(rate=rate, capacity=burst)
        return self._buckets[domain]

    def wait_for_slot(self, domain: str) -> float:
        """Block until a request slot is available. Returns actual wait time."""
        bucket = self._get_bucket(domain)
        wait = bucket.consume()
        if wait > 0:
            time.sleep(wait)
        return wait

    def get_stats(self) -> dict:
        return {
            domain: {"tokens": round(bucket._tokens, 2), "rate": bucket.rate}
            for domain, bucket in self._buckets.items()
        }
