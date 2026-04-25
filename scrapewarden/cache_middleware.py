"""Middleware wrapper around CachePolicy for scrapewarden."""
from __future__ import annotations

from typing import Callable, Dict, Optional

from .cache_policy import CachePolicy, CachePolicyConfig, _CacheEntry


class CacheMiddleware:
    """Thin middleware that integrates CachePolicy into a request pipeline."""

    def __init__(self, config: Optional[CachePolicyConfig] = None) -> None:
        self._policy = CachePolicy(config)
        self._hits: int = 0
        self._misses: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "CacheMiddleware":
        return cls(config=CachePolicyConfig.from_dict(data))

    def on_request(self, method: str, url: str) -> Optional[_CacheEntry]:
        """Return a cached entry if available, otherwise None (cache miss)."""
        if not self._policy.is_cacheable_request(method):
            return None
        entry = self._policy.get(method, url)
        if entry is not None:
            self._hits += 1
            return entry
        self._misses += 1
        return None

    def on_response(
        self,
        method: str,
        url: str,
        status_code: int,
        body: bytes,
        headers: Dict[str, str],
    ) -> None:
        """Store the response in cache if eligible."""
        self._policy.put(method, url, status_code, body, headers)

    def invalidate(self, method: str, url: str) -> None:
        self._policy.invalidate(method, url)

    def clear(self) -> None:
        self._policy.clear()
        self._hits = 0
        self._misses = 0

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> dict:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 4),
            "cache_size": self._policy.size(),
        }
