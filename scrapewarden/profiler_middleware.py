"""Middleware that integrates RequestProfiler into the scraping pipeline."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from .domain_utils import extract_domain
from .request_profiler import ProfilerConfig, RequestProfiler


class ProfilerMiddleware:
    """Records per-domain timing and byte metrics for each request/response pair."""

    def __init__(self, profiler: Optional[RequestProfiler] = None) -> None:
        self._profiler = profiler or RequestProfiler()
        self._pending: Dict[str, float] = {}  # request_id -> start time

    @classmethod
    def from_dict(cls, data: dict) -> "ProfilerMiddleware":
        config = ProfilerConfig.from_dict(data)
        return cls(profiler=RequestProfiler(config))

    # ------------------------------------------------------------------
    # Pipeline hooks
    # ------------------------------------------------------------------

    def on_request(self, request_id: str, url: str, body: bytes = b"") -> None:
        """Call before sending a request."""
        self._pending[request_id] = time.monotonic()

    def on_response(
        self,
        request_id: str,
        url: str,
        status_code: int,
        response_body: bytes = b"",
        request_body: bytes = b"",
    ) -> None:
        """Call after receiving a response."""
        start = self._pending.pop(request_id, None)
        if start is None:
            return
        elapsed = time.monotonic() - start
        domain = extract_domain(url)
        self._profiler.record(
            domain,
            elapsed=elapsed,
            req_bytes=len(request_body),
            resp_bytes=len(response_body),
            status=status_code,
        )

    # ------------------------------------------------------------------
    # Inspection helpers
    # ------------------------------------------------------------------

    def profile(self, url_or_domain: str) -> dict:
        domain = extract_domain(url_or_domain) or url_or_domain
        return self._profiler.profile(domain)

    def all_profiles(self) -> Dict[str, Any]:
        return self._profiler.all_profiles()

    def slow_domains(self, threshold: Optional[float] = None) -> list:
        return self._profiler.slow_domains(threshold)
