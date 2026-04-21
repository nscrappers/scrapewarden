"""Lightweight in-memory stats collector for scrapewarden middleware."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DomainStats:
    domain: str
    total_requests: int = 0
    success_count: int = 0
    failure_count: int = 0
    retry_count: int = 0
    blocked_count: int = 0
    total_wait_seconds: float = 0.0
    status_codes: Dict[int, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def failure_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.failure_count / self.total_requests

    @property
    def avg_wait_seconds(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_wait_seconds / self.total_requests

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "total_requests": self.total_requests,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "retry_count": self.retry_count,
            "blocked_count": self.blocked_count,
            "failure_rate": round(self.failure_rate, 4),
            "avg_wait_seconds": round(self.avg_wait_seconds, 4),
            "status_codes": dict(self.status_codes),
        }


class StatsCollector:
    """Aggregates per-domain request statistics."""

    def __init__(self) -> None:
        self._data: Dict[str, DomainStats] = {}

    def _get(self, domain: str) -> DomainStats:
        if domain not in self._data:
            self._data[domain] = DomainStats(domain=domain)
        return self._data[domain]

    def record_request(
        self,
        domain: str,
        status_code: Optional[int] = None,
        success: bool = True,
        retried: bool = False,
        blocked: bool = False,
        wait_seconds: float = 0.0,
    ) -> None:
        s = self._get(domain)
        s.total_requests += 1
        s.total_wait_seconds += wait_seconds
        if success:
            s.success_count += 1
        else:
            s.failure_count += 1
        if retried:
            s.retry_count += 1
        if blocked:
            s.blocked_count += 1
        if status_code is not None:
            s.status_codes[status_code] += 1

    def get(self, domain: str) -> Optional[DomainStats]:
        return self._data.get(domain)

    def all_domains(self) -> List[str]:
        return list(self._data.keys())

    def summary(self) -> List[dict]:
        return [s.to_dict() for s in self._data.values()]

    def reset(self, domain: Optional[str] = None) -> None:
        if domain is not None:
            self._data.pop(domain, None)
        else:
            self._data.clear()
