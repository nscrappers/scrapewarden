"""Statistics tracking for response cache hits, misses, and evictions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class _DomainCacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    bytes_saved: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "bytes_saved": self.bytes_saved,
            "hit_rate": round(self.hit_rate, 4),
        }


class ResponseCacheStats:
    """Aggregates cache performance metrics per domain."""

    def __init__(self) -> None:
        self._domains: Dict[str, _DomainCacheStats] = {}

    def _get(self, domain: str) -> _DomainCacheStats:
        if domain not in self._domains:
            self._domains[domain] = _DomainCacheStats()
        return self._domains[domain]

    def record_hit(self, domain: str, bytes_saved: int = 0) -> None:
        s = self._get(domain)
        s.hits += 1
        s.bytes_saved += bytes_saved

    def record_miss(self, domain: str) -> None:
        self._get(domain).misses += 1

    def record_eviction(self, domain: str) -> None:
        self._get(domain).evictions += 1

    def hit_rate(self, domain: str) -> float:
        return self._get(domain).hit_rate

    def total_hits(self) -> int:
        return sum(s.hits for s in self._domains.values())

    def total_misses(self) -> int:
        return sum(s.misses for s in self._domains.values())

    def total_bytes_saved(self) -> int:
        return sum(s.bytes_saved for s in self._domains.values())

    def domain_stats(self, domain: str) -> Optional[dict]:
        if domain not in self._domains:
            return None
        return self._domains[domain].to_dict()

    def to_dict(self) -> dict:
        return {
            "domains": {d: s.to_dict() for d, s in self._domains.items()},
            "total_hits": self.total_hits(),
            "total_misses": self.total_misses(),
            "total_bytes_saved": self.total_bytes_saved(),
        }

    def reset(self) -> None:
        self._domains.clear()
