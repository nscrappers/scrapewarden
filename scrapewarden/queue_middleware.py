"""Middleware that routes requests through the priority RequestQueue."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .request_queue import QueueConfig, RequestQueue


class QueueMiddleware:
    """Wraps RequestQueue to integrate with the ScrapeWarden middleware chain."""

    def __init__(self, config: Optional[QueueConfig] = None) -> None:
        self.config = config or QueueConfig()
        self._queue = RequestQueue(self.config)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueueMiddleware":
        return cls(config=QueueConfig.from_dict(data))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, request: Any, domain: str = "", priority: Optional[int] = None) -> bool:
        """Enqueue a request. Returns False when the queue is full."""
        return self._queue.enqueue(request, domain=domain, priority=priority)

    def next_request(self) -> Optional[Any]:
        """Dequeue the next eligible request or return None."""
        return self._queue.dequeue()

    def drain(self, handler: Callable[[Any], None]) -> int:
        """Drain all currently eligible requests through *handler*.

        Returns the number of requests processed.
        """
        processed = 0
        while True:
            req = self._queue.dequeue()
            if req is None:
                break
            handler(req)
            processed += 1
        return processed

    @property
    def size(self) -> int:
        return self._queue.size

    @property
    def is_full(self) -> bool:
        return self._queue.is_full()

    def reset(self) -> None:
        self._queue.clear()
