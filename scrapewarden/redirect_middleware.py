from __future__ import annotations

from typing import Optional

from .redirect_tracker import (
    RedirectConfig,
    RedirectChain,
    RedirectTracker,
    TooManyRedirectsError,
    CrossDomainRedirectError,
)
from .stats_collector import StatsCollector
from .domain_utils import extract_domain


class RedirectMiddleware:
    """Middleware that tracks and enforces redirect policies per request."""

    def __init__(
        self,
        config: Optional[RedirectConfig] = None,
        stats: Optional[StatsCollector] = None,
    ) -> None:
        self.config = config or RedirectConfig()
        self._tracker = RedirectTracker(self.config)
        self._stats = stats
        self._blocked: int = 0

    @classmethod
    def from_dict(cls, data: dict, stats: Optional[StatsCollector] = None) -> "RedirectMiddleware":
        return cls(config=RedirectConfig.from_dict(data), stats=stats)

    def on_request(self, request_id: str, url: str) -> None:
        """Call when a new request is initiated."""
        self._tracker.start(request_id, url)

    def on_redirect(self, request_id: str, new_url: str) -> bool:
        """
        Call when a redirect response is received.
        Returns True if the redirect is allowed, False if it should be blocked.
        Records stats if a StatsCollector is provided.
        """
        try:
            self._tracker.record(request_id, new_url)
            return True
        except (TooManyRedirectsError, CrossDomainRedirectError, ValueError) as exc:
            self._blocked += 1
            if self._stats:
                domain = extract_domain(new_url)
                self._stats.record_failure(domain, error=str(exc))
            return False

    def on_complete(self, request_id: str) -> Optional[RedirectChain]:
        """Call when a request completes. Returns the redirect chain and clears it."""
        chain = self._tracker.get(request_id)
        self._tracker.clear(request_id)
        return chain

    @property
    def blocked_count(self) -> int:
        return self._blocked

    def chain_for(self, request_id: str) -> Optional[RedirectChain]:
        return self._tracker.get(request_id)
