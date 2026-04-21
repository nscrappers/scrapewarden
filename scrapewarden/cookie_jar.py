"""Per-domain cookie jar management for stateful scraping sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from http.cookiejar import CookieJar
from typing import Dict, Optional
import time


@dataclass
class CookieJarConfig:
    enabled: bool = True
    max_cookies_per_domain: int = 50
    ttl_seconds: Optional[float] = 3600.0  # None = no expiry
    isolate_by_domain: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "CookieJarConfig":
        return cls(
            enabled=data.get("enabled", True),
            max_cookies_per_domain=data.get("max_cookies_per_domain", 50),
            ttl_seconds=data.get("ttl_seconds", 3600.0),
            isolate_by_domain=data.get("isolate_by_domain", True),
        )


@dataclass
class _JarEntry:
    jar: CookieJar
    created_at: float = field(default_factory=time.monotonic)
    cookie_count: int = 0


class DomainCookieJar:
    """Manages isolated cookie jars keyed by domain."""

    def __init__(self, config: Optional[CookieJarConfig] = None) -> None:
        self._config = config or CookieJarConfig()
        self._jars: Dict[str, _JarEntry] = {}

    def _is_expired(self, entry: _JarEntry) -> bool:
        if self._config.ttl_seconds is None:
            return False
        return (time.monotonic() - entry.created_at) > self._config.ttl_seconds

    def get_jar(self, domain: str) -> Optional[CookieJar]:
        """Return the cookie jar for a domain, or None if disabled/expired."""
        if not self._config.enabled:
            return None
        key = domain if self._config.isolate_by_domain else "__global__"
        entry = self._jars.get(key)
        if entry is None:
            entry = _JarEntry(jar=CookieJar())
            self._jars[key] = entry
        elif self._is_expired(entry):
            entry = _JarEntry(jar=CookieJar())
            self._jars[key] = entry
        return entry.jar

    def record_cookies(self, domain: str, count: int) -> None:
        """Update the cookie count for a domain jar."""
        key = domain if self._config.isolate_by_domain else "__global__"
        entry = self._jars.get(key)
        if entry:
            entry.cookie_count = min(count, self._config.max_cookies_per_domain)

    def clear(self, domain: str) -> None:
        """Clear cookies for a specific domain."""
        key = domain if self._config.isolate_by_domain else "__global__"
        self._jars.pop(key, None)

    def clear_all(self) -> None:
        """Clear all stored jars."""
        self._jars.clear()

    def domain_count(self) -> int:
        return len(self._jars)

    def cookie_count(self, domain: str) -> int:
        key = domain if self._config.isolate_by_domain else "__global__"
        entry = self._jars.get(key)
        return entry.cookie_count if entry else 0
