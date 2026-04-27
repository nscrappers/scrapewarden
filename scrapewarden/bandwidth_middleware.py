"""Middleware that integrates BandwidthTracker into the request/response lifecycle."""
from __future__ import annotations

from typing import Dict, Optional

from .bandwidth_tracker import BandwidthConfig, BandwidthTracker
from .domain_utils import extract_domain


class BandwidthMiddleware:
    """Attach to a scraping pipeline to monitor and optionally gate bandwidth."""

    def __init__(self, config: Optional[BandwidthConfig] = None) -> None:
        self._tracker = BandwidthTracker(config or BandwidthConfig())
        self._blocked: Dict[str, bool] = {}

    @classmethod
    def from_dict(cls, data: dict) -> "BandwidthMiddleware":
        return cls(BandwidthConfig.from_dict(data))

    # ------------------------------------------------------------------
    # Pipeline hooks
    # ------------------------------------------------------------------

    def on_request(self, url: str, headers: Optional[dict] = None, body: bytes = b"") -> bool:
        """Call before sending a request. Returns False if domain is over limit."""
        domain = extract_domain(url)
        if self._tracker.is_over_limit(domain):
            self._blocked[domain] = True
            return False
        request_size = len(body) + sum(
            len(k) + len(v) for k, v in (headers or {}).items()
        )
        self._tracker.record(domain, bytes_sent=request_size)
        return True

    def on_response(self, url: str, body: bytes = b"", headers: Optional[dict] = None) -> None:
        """Call after receiving a response to record inbound bytes."""
        domain = extract_domain(url)
        response_size = len(body) + sum(
            len(k) + len(v) for k, v in (headers or {}).items()
        )
        self._tracker.record(domain, bytes_received=response_size)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def is_blocked(self, domain: str) -> bool:
        return self._blocked.get(domain, False)

    def stats(self, domain: Optional[str] = None) -> dict:
        if domain:
            return self._tracker.stats(domain)
        return self._tracker.all_stats()

    def reset(self, domain: Optional[str] = None) -> None:
        self._tracker.reset(domain)
        if domain:
            self._blocked.pop(domain, None)
        else:
            self._blocked.clear()
