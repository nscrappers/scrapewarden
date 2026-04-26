"""Middleware wrapper around RequestScheduler for use with scraping pipelines."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .domain_utils import extract_domain
from .request_scheduler import RequestScheduler, SchedulerConfig


class SchedulerMiddleware:
    """Enqueues outgoing requests and serves them in priority + cooldown order."""

    def __init__(self, scheduler: Optional[RequestScheduler] = None) -> None:
        self._scheduler = scheduler or RequestScheduler()
        self._submitted: int = 0
        self._dropped: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SchedulerMiddleware":
        return cls(RequestScheduler(SchedulerConfig.from_dict(data)))

    def on_request(self, request: Any, priority: Optional[int] = None) -> bool:
        """Submit *request* to the internal scheduler.

        *request* must expose a ``url`` attribute (str).
        Returns True if enqueued, False if the queue was full.
        """
        url: str = getattr(request, "url", "") or ""
        domain = extract_domain(url) or "unknown"
        accepted = self._scheduler.submit(request, domain=domain, priority=priority)
        if accepted:
            self._submitted += 1
        else:
            self._dropped += 1
        return accepted

    def next_request(self) -> Optional[Any]:
        """Return the next request to dispatch, or None if none is ready."""
        return self._scheduler.next_request()

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    @property
    def queue_size(self) -> int:
        return self._scheduler.size

    @property
    def submitted(self) -> int:
        return self._submitted

    @property
    def dropped(self) -> int:
        return self._dropped

    def stats(self) -> Dict[str, Any]:
        return {
            "queue_size": self.queue_size,
            "submitted": self._submitted,
            "dropped": self._dropped,
        }
