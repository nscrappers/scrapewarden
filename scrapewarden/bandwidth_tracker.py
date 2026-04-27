"""Tracks bandwidth usage (bytes sent/received) per domain."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class BandwidthConfig:
    max_bytes_per_domain: Optional[int] = None  # None = unlimited
    warn_threshold_bytes: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> "BandwidthConfig":
        return cls(
            max_bytes_per_domain=data.get("max_bytes_per_domain"),
            warn_threshold_bytes=data.get("warn_threshold_bytes"),
        )


@dataclass
class _DomainBandwidth:
    bytes_sent: int = 0
    bytes_received: int = 0
    request_count: int = 0

    @property
    def total_bytes(self) -> int:
        return self.bytes_sent + self.bytes_received

    def to_dict(self) -> dict:
        return {
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "total_bytes": self.total_bytes,
            "request_count": self.request_count,
        }


class BandwidthTracker:
    def __init__(self, config: Optional[BandwidthConfig] = None) -> None:
        self._config = config or BandwidthConfig()
        self._domains: Dict[str, _DomainBandwidth] = {}

    def _get(self, domain: str) -> _DomainBandwidth:
        if domain not in self._domains:
            self._domains[domain] = _DomainBandwidth()
        return self._domains[domain]

    def record(self, domain: str, bytes_sent: int = 0, bytes_received: int = 0) -> None:
        entry = self._get(domain)
        entry.bytes_sent += max(0, bytes_sent)
        entry.bytes_received += max(0, bytes_received)
        entry.request_count += 1

    def is_over_limit(self, domain: str) -> bool:
        limit = self._config.max_bytes_per_domain
        if limit is None:
            return False
        return self._get(domain).total_bytes >= limit

    def is_near_limit(self, domain: str) -> bool:
        warn = self._config.warn_threshold_bytes
        if warn is None:
            return False
        return self._get(domain).total_bytes >= warn

    def stats(self, domain: str) -> dict:
        return self._get(domain).to_dict()

    def all_stats(self) -> Dict[str, dict]:
        return {d: v.to_dict() for d, v in self._domains.items()}

    def reset(self, domain: Optional[str] = None) -> None:
        if domain:
            self._domains.pop(domain, None)
        else:
            self._domains.clear()
