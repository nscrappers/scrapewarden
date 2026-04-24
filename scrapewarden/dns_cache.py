"""DNS resolution cache to avoid repeated lookups during scraping."""
from __future__ import annotations

import socket
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass
class DNSCacheConfig:
    ttl_seconds: float = 300.0
    max_entries: int = 1000
    fallback_on_error: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "DNSCacheConfig":
        return cls(
            ttl_seconds=float(data.get("ttl_seconds", 300.0)),
            max_entries=int(data.get("max_entries", 1000)),
            fallback_on_error=bool(data.get("fallback_on_error", True)),
        )


@dataclass
class _CacheEntry:
    address: str
    expires_at: float

    def is_expired(self) -> bool:
        return time.monotonic() >= self.expires_at


class DNSCache:
    """Thread-safe in-process DNS cache with TTL expiry."""

    def __init__(self, config: Optional[DNSCacheConfig] = None) -> None:
        self._config = config or DNSCacheConfig()
        self._cache: Dict[str, _CacheEntry] = {}

    def resolve(self, hostname: str) -> str:
        """Return cached IP for hostname, resolving if needed."""
        entry = self._cache.get(hostname)
        if entry and not entry.is_expired():
            return entry.address

        try:
            address = socket.gethostbyname(hostname)
        except socket.gaierror:
            if self._config.fallback_on_error and entry:
                return entry.address
            raise

        self._evict_if_needed()
        self._cache[hostname] = _CacheEntry(
            address=address,
            expires_at=time.monotonic() + self._config.ttl_seconds,
        )
        return address

    def invalidate(self, hostname: str) -> None:
        """Remove a specific hostname from the cache."""
        self._cache.pop(hostname, None)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def _evict_if_needed(self) -> None:
        now = time.monotonic()
        expired = [h for h, e in self._cache.items() if e.expires_at <= now]
        for h in expired:
            del self._cache[h]
        if len(self._cache) >= self._config.max_entries:
            oldest = min(self._cache, key=lambda h: self._cache[h].expires_at)
            del self._cache[oldest]

    @property
    def size(self) -> int:
        return len(self._cache)

    def cached_hostnames(self) -> Tuple[str, ...]:
        return tuple(self._cache.keys())
