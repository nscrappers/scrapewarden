"""Priority-based request scheduler with domain-aware ordering."""
from __future__ import annotations

import heapq
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class SchedulerConfig:
    max_queue_size: int = 1000
    default_priority: int = 5  # 1 (highest) – 10 (lowest)
    domain_cooldown: float = 0.5  # seconds between requests to same domain

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SchedulerConfig":
        return cls(
            max_queue_size=int(data.get("max_queue_size", 1000)),
            default_priority=int(data.get("default_priority", 5)),
            domain_cooldown=float(data.get("domain_cooldown", 0.5)),
        )


@dataclass(order=True)
class _ScheduledRequest:
    priority: int
    enqueued_at: float
    request: Any = field(compare=False)
    domain: str = field(compare=False)


class RequestScheduler:
    """Min-heap scheduler that respects per-domain cooldown windows."""

    def __init__(self, config: Optional[SchedulerConfig] = None) -> None:
        self.config = config or SchedulerConfig()
        self._heap: list[_ScheduledRequest] = []
        self._domain_last_sent: Dict[str, float] = {}
        self._skipped: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RequestScheduler":
        return cls(SchedulerConfig.from_dict(data))

    def submit(self, request: Any, domain: str, priority: Optional[int] = None) -> bool:
        """Add a request to the scheduler. Returns False if queue is full."""
        if len(self._heap) >= self.config.max_queue_size:
            return False
        p = priority if priority is not None else self.config.default_priority
        entry = _ScheduledRequest(
            priority=p,
            enqueued_at=time.monotonic(),
            request=request,
            domain=domain,
        )
        heapq.heappush(self._heap, entry)
        return True

    def next_request(self) -> Optional[Any]:
        """Pop the highest-priority request whose domain cooldown has elapsed."""
        now = time.monotonic()
        candidates: list[_ScheduledRequest] = []
        result: Optional[_ScheduledRequest] = None

        while self._heap:
            entry = heapq.heappop(self._heap)
            last = self._domain_last_sent.get(entry.domain, 0.0)
            if now - last >= self.config.domain_cooldown:
                result = entry
                break
            candidates.append(entry)

        for c in candidates:
            heapq.heappush(self._heap, c)

        if result is None:
            return None

        self._domain_last_sent[result.domain] = now
        return result.request

    @property
    def size(self) -> int:
        return len(self._heap)

    @property
    def skipped(self) -> int:
        return self._skipped
