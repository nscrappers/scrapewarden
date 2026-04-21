"""Deduplication layer that wraps ScrapeWardenMiddleware to skip seen requests."""

from __future__ import annotations

from typing import Any, Callable, Coroutine, Optional

from scrapewarden.request_deduplicator import DeduplicatorConfig, RequestDeduplicator


class DedupMiddleware:
    """Middleware that drops duplicate requests before they reach the network.

    Usage (httpx-style)::

        dedup = DedupMiddleware()

        async def transport(url, method="GET", body=b"", **kwargs):
            return await real_transport(url, method=method, body=body, **kwargs)

        result = await dedup.handle(url, method, body, transport)
    """

    def __init__(self, config: Optional[DeduplicatorConfig] = None) -> None:
        self._deduplicator = RequestDeduplicator(config)
        self._skipped: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def handle(
        self,
        url: str,
        method: str = "GET",
        body: bytes = b"",
        next_handler: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None,
    ) -> Optional[Any]:
        """Process a request, skipping it if already seen.

        Returns the response from *next_handler* or ``None`` for duplicates.
        """
        if self._deduplicator.check_and_mark(url, method=method, body=body):
            self._skipped += 1
            return None

        if next_handler is not None:
            return await next_handler(url, method=method, body=body)
        return None

    def reset(self) -> None:
        """Clear deduplication state and counters."""
        self._deduplicator.clear()
        self._skipped = 0

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def skipped(self) -> int:
        """Total number of duplicate requests skipped."""
        return self._skipped

    @property
    def seen_count(self) -> int:
        """Number of unique requests tracked."""
        return self._deduplicator.size

    def stats(self) -> dict:
        return {
            "seen_count": self.seen_count,
            "skipped": self.skipped,
        }
