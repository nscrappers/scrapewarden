"""Response caching policy for scrapewarden."""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass
class CachePolicyConfig:
    enabled: bool = True
    ttl_seconds: int = 300
    max_size: int = 1000
    cacheable_methods: Tuple[str, ...] = ("GET", "HEAD")
    cacheable_status_codes: Tuple[int, ...] = (200, 203, 204, 300, 301, 410)

    @classmethod
    def from_dict(cls, data: dict) -> "CachePolicyConfig":
        return cls(
            enabled=data.get("enabled", True),
            ttl_seconds=int(data.get("ttl_seconds", 300)),
            max_size=int(data.get("max_size", 1000)),
            cacheable_methods=tuple(data.get("cacheable_methods", ["GET", "HEAD"])),
            cacheable_status_codes=tuple(
                int(s) for s in data.get("cacheable_status_codes", [200, 203, 204, 300, 301, 410])
            ),
        )


@dataclass
class _CacheEntry:
    body: bytes
    status_code: int
    headers: Dict[str, str]
    expires_at: float

    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at


class CachePolicy:
    def __init__(self, config: Optional[CachePolicyConfig] = None) -> None:
        self.config = config or CachePolicyConfig()
        self._store: Dict[str, _CacheEntry] = {}

    def _make_key(self, method: str, url: str) -> str:
        raw = f"{method.upper()}:{url}"
        return hashlib.sha1(raw.encode()).hexdigest()

    def is_cacheable_request(self, method: str) -> bool:
        return self.config.enabled and method.upper() in self.config.cacheable_methods

    def is_cacheable_response(self, status_code: int) -> bool:
        return status_code in self.config.cacheable_status_codes

    def get(self, method: str, url: str) -> Optional[_CacheEntry]:
        key = self._make_key(method, url)
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            del self._store[key]
            return None
        return entry

    def put(self, method: str, url: str, status_code: int, body: bytes, headers: Dict[str, str]) -> None:
        if not self.is_cacheable_request(method) or not self.is_cacheable_response(status_code):
            return
        if len(self._store) >= self.config.max_size:
            oldest = next(iter(self._store))
            del self._store[oldest]
        key = self._make_key(method, url)
        self._store[key] = _CacheEntry(
            body=body,
            status_code=status_code,
            headers=headers,
            expires_at=time.monotonic() + self.config.ttl_seconds,
        )

    def invalidate(self, method: str, url: str) -> None:
        key = self._make_key(method, url)
        self._store.pop(key, None)

    def size(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        self._store.clear()
