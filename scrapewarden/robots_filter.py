"""robots.txt compliance filter for scrapewarden."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser


@dataclass
class RobotsConfig:
    user_agent: str = "*"
    respect_robots: bool = True
    cache_ttl: int = 3600  # seconds

    @classmethod
    def from_dict(cls, data: dict) -> "RobotsConfig":
        return cls(
            user_agent=data.get("user_agent", "*"),
            respect_robots=data.get("respect_robots", True),
            cache_ttl=int(data.get("cache_ttl", 3600)),
        )


@dataclass
class _CacheEntry:
    parser: RobotFileParser
    fetched_at: float


class RobotsFilter:
    """Checks URLs against robots.txt rules, with per-domain caching."""

    def __init__(self, config: Optional[RobotsConfig] = None) -> None:
        self.config = config or RobotsConfig()
        self._cache: Dict[str, _CacheEntry] = {}

    def _robots_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    def _get_parser(self, url: str) -> Optional[RobotFileParser]:
        robots_url = self._robots_url(url)
        now = time.monotonic()
        entry = self._cache.get(robots_url)

        if entry and (now - entry.fetched_at) < self.config.cache_ttl:
            return entry.parser

        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            parser.read()
        except Exception:
            # If we can't fetch robots.txt, allow the request
            return None

        self._cache[robots_url] = _CacheEntry(parser=parser, fetched_at=now)
        return parser

    def is_allowed(self, url: str) -> bool:
        """Return True if the URL is allowed by robots.txt."""
        if not self.config.respect_robots:
            return True

        parser = self._get_parser(url)
        if parser is None:
            return True

        return parser.can_fetch(self.config.user_agent, url)

    def clear_cache(self) -> None:
        """Evict all cached robots.txt entries."""
        self._cache.clear()

    @property
    def cached_domains(self) -> int:
        return len(self._cache)
