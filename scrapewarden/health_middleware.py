"""Middleware that records per-domain health after each response or error."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from .health_monitor import HealthConfig, HealthMonitor


class HealthMiddleware:
    """Wraps HealthMonitor to integrate with request/response lifecycle hooks."""

    def __init__(self, config: Optional[HealthConfig] = None) -> None:
        self.monitor = HealthMonitor(config)
        self._start_times: Dict[str, float] = {}

    @classmethod
    def from_dict(cls, data: dict) -> "HealthMiddleware":
        return cls(config=HealthConfig.from_dict(data))

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def on_request(self, request_id: str, domain: str) -> None:
        """Call before sending a request to start the timer."""
        self._start_times[request_id] = time.monotonic()

    def on_response(
        self,
        request_id: str,
        domain: str,
        status_code: int,
        *,
        success: Optional[bool] = None,
    ) -> None:
        """Call after receiving a response."""
        elapsed = self._elapsed(request_id)
        if success is None:
            success = 200 <= status_code < 400
        self.monitor.record(domain, success, elapsed)

    def on_error(self, request_id: str, domain: str) -> None:
        """Call when a network-level error occurs."""
        elapsed = self._elapsed(request_id)
        self.monitor.record(domain, False, elapsed)

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    def is_healthy(self, domain: str) -> bool:
        return self.monitor.is_healthy(domain)

    def stats(self) -> Dict[str, Any]:
        return self.monitor.all_stats()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _elapsed(self, request_id: str) -> float:
        start = self._start_times.pop(request_id, None)
        return (time.monotonic() - start) if start is not None else 0.0
