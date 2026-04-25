"""Lightweight statistics tracker for the RequestQueue."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class _DomainQueueStats:
    enqueued: int = 0
    dequeued: int = 0
    dropped: int = 0
    total_wait: float = 0.0

    @property
    def avg_wait(self) -> float:
        return self.total_wait / self.dequeued if self.dequeued else 0.0

    def to_dict(self) -> Dict:
        return {
            "enqueued": self.enqueued,
            "dequeued": self.dequeued,
            "dropped": self.dropped,
            "avg_wait_seconds": round(self.avg_wait, 4),
        }


class QueueStats:
    """Records enqueue/dequeue events and computes per-domain statistics."""

    def __init__(self) -> None:
        self._domains: Dict[str, _DomainQueueStats] = {}
        self._enqueue_times: Dict[int, float] = {}  # id(request) -> monotonic time

    def _get(self, domain: str) -> _DomainQueueStats:
        if domain not in self._domains:
            self._domains[domain] = _DomainQueueStats()
        return self._domains[domain]

    def record_enqueue(self, request: object, domain: str) -> None:
        self._get(domain).enqueued += 1
        self._enqueue_times[id(request)] = time.monotonic()

    def record_dequeue(self, request: object, domain: str) -> None:
        stats = self._get(domain)
        stats.dequeued += 1
        enqueued_at = self._enqueue_times.pop(id(request), None)
        if enqueued_at is not None:
            stats.total_wait += time.monotonic() - enqueued_at

    def record_drop(self, domain: str) -> None:
        self._get(domain).dropped += 1

    def domain_stats(self, domain: str) -> Dict:
        return self._get(domain).to_dict()

    def all_stats(self) -> Dict[str, Dict]:
        return {d: s.to_dict() for d, s in self._domains.items()}

    def reset(self) -> None:
        self._domains.clear()
        self._enqueue_times.clear()
