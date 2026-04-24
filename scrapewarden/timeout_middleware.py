from __future__ import annotations

from typing import Optional

from .timeout_manager import TimeoutConfig, TimeoutManager
from .domain_utils import extract_domain


class TimeoutMiddleware:
    """Middleware that resolves per-request timeouts and tracks timeout events."""

    def __init__(self, manager: Optional[TimeoutManager] = None) -> None:
        self._manager = manager or TimeoutManager()

    @classmethod
    def from_dict(cls, data: dict) -> "TimeoutMiddleware":
        config = TimeoutConfig.from_dict(data)
        return cls(manager=TimeoutManager(config=config))

    def get_timeouts(self, url: str) -> dict:
        """Return a dict with 'timeout' and 'connect_timeout' for the given URL."""
        domain = extract_domain(url)
        return {
            "timeout": self._manager.get_timeout(domain),
            "connect_timeout": self._manager.get_connect_timeout(domain),
        }

    def on_timeout(self, url: str) -> None:
        """Call when a request to *url* timed out."""
        domain = extract_domain(url)
        self._manager.record_timeout(domain)

    def on_success(self, url: str) -> None:
        """Call when a request to *url* completed successfully."""
        domain = extract_domain(url)
        self._manager.record_success(domain)

    def timeout_count(self, url: str) -> int:
        domain = extract_domain(url)
        return self._manager.timeout_count(domain)

    def reset(self) -> None:
        self._manager.reset()
