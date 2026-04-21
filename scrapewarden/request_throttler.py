"""Domain-level request throttling with configurable delays between requests."""

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ThrottleConfig:
    default_delay: float = 1.0  # seconds between requests to same domain
    max_delay: float = 60.0
    per_domain_delays: Dict[str, float] = field(default_factory=dict)
    jitter: float = 0.0  # random jitter fraction (0.0 to 1.0)

    @classmethod
    def from_dict(cls, data: dict) -> "ThrottleConfig":
        return cls(
            default_delay=float(data.get("default_delay", 1.0)),
            max_delay=float(data.get("max_delay", 60.0)),
            per_domain_delays=data.get("per_domain_delays", {}),
            jitter=float(data.get("jitter", 0.0)),
        )


class RequestThrottler:
    """Tracks last request time per domain and enforces minimum delays."""

    def __init__(self, config: Optional[ThrottleConfig] = None):
        self.config = config or ThrottleConfig()
        self._last_request: Dict[str, float] = {}
        self._lock = threading.Lock()

    def wait_if_needed(self, domain: str) -> float:
        """Block until the domain-specific delay has elapsed.
        Returns the actual time waited in seconds."""
        import random

        delay = self.config.per_domain_delays.get(domain, self.config.default_delay)
        if self.config.jitter > 0.0:
            delay += delay * self.config.jitter * random.random()
        delay = min(delay, self.config.max_delay)

        with self._lock:
            now = time.monotonic()
            last = self._last_request.get(domain, 0.0)
            elapsed = now - last
            wait_time = max(0.0, delay - elapsed)
            if wait_time > 0:
                time.sleep(wait_time)
            self._last_request[domain] = time.monotonic()
            return wait_time

    def time_until_ready(self, domain: str) -> float:
        """Return seconds until the domain is ready for the next request (non-blocking)."""
        delay = self.config.per_domain_delays.get(domain, self.config.default_delay)
        delay = min(delay, self.config.max_delay)
        with self._lock:
            now = time.monotonic()
            last = self._last_request.get(domain, 0.0)
            return max(0.0, delay - (now - last))

    def reset(self, domain: Optional[str] = None) -> None:
        """Reset throttle state for a domain or all domains."""
        with self._lock:
            if domain:
                self._last_request.pop(domain, None)
            else:
                self._last_request.clear()
