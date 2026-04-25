"""Priority-based request queue with domain-aware scheduling."""
from __future__ import annotations

import heapq
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class QueueConfig:
    max_size: int = 1000
    default_priority: int = 5  # 1 (highest) – 10 (lowest)
    domain_slot_interval: float = 0.5  # seconds between requests per domain

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueueConfig":
        return cls(
            max_size=data.get("max_size", 1000),
            default_priority=data.get("default_priority", 5),
            domain_slot_interval=data.get("domain_slot_interval", 0.5),
        )


@dataclass(order=True)
class _QueueEntry:
    priority: int
    enqueued_at: float
    request: Any = field(compare=False)
    domain: str = field(compare=False, default="")


class RequestQueue:
    """Thread-safe priority queue that enforces per-domain slot intervals."""

    def __init__(self, config: Optional[QueueConfig] = None) -> None:
        self.config = config or QueueConfig()
        self._heap: list[_QueueEntry] = []
        self._domain_last_sent: Dict[str, float] = {}
        self._size = 0

    @property
    def size(self) -> int:
        return self._size

    def is_full(self) -> bool:
        return self._size >= self.config.max_size

    def enqueue(self, request: Any, domain: str = "", priority: Optional[int] = None) -> bool:
        """Add a request. Returns False if queue is full."""
        if self.is_full():
            return False
        p = priority if priority is not None else self.config.default_priority
        entry = _QueueEntry(priority=p, enqueued_at=time.monotonic(), request=request, domain=domain)
        heapq.heappush(self._heap, entry)
        self._size += 1
        return True

    def dequeue(self) -> Optional[Any]:
        """Return the next request respecting domain slot intervals, or None."""
        skipped: list[_QueueEntry] = []
        result = None
        now = time.monotonic()

        while self._heap:
            entry = heapq.heappop(self._heap)
            last = self._domain_last_sent.get(entry.domain, 0.0)
            if now - last >= self.config.domain_slot_interval:
                self._domain_last_sent[entry.domain] = now
                self._size -= 1
                result = entry.request
                break
            skipped.append(entry)

        for s in skipped:
            heapq.heappush(self._heap, s)

        return result

    def clear(self) -> None:
        self._heap.clear()
        self._domain_last_sent.clear()
        self._size = 0
