from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ProxyEntry:
    url: str
    fail_count: int = 0
    last_used: float = 0.0
    banned_until: float = 0.0

    @property
    def is_banned(self) -> bool:
        return time.monotonic() < self.banned_until

    def mark_failure(self, ban_duration: float = 60.0) -> None:
        self.fail_count += 1
        if self.fail_count >= 3:
            self.banned_until = time.monotonic() + ban_duration

    def mark_success(self) -> None:
        self.fail_count = 0
        self.banned_until = 0.0


@dataclass
class ProxyRotator:
    proxies: List[ProxyEntry] = field(default_factory=list)
    strategy: str = "round_robin"  # round_robin | random | least_used
    ban_duration: float = 60.0
    _index: int = field(default=0, init=False, repr=False)

    @classmethod
    def from_list(cls, proxy_urls: List[str], **kwargs) -> "ProxyRotator":
        entries = [ProxyEntry(url=url) for url in proxy_urls]
        return cls(proxies=entries, **kwargs)

    def _available(self) -> List[ProxyEntry]:
        return [p for p in self.proxies if not p.is_banned]

    def get_proxy(self) -> Optional[ProxyEntry]:
        available = self._available()
        if not available:
            return None

        if self.strategy == "random":
            proxy = random.choice(available)
        elif self.strategy == "least_used":
            proxy = min(available, key=lambda p: p.last_used)
        else:  # round_robin
            self._index = self._index % len(available)
            proxy = available[self._index]
            self._index += 1

        proxy.last_used = time.monotonic()
        return proxy

    def report_failure(self, proxy_url: str) -> None:
        for p in self.proxies:
            if p.url == proxy_url:
                p.mark_failure(self.ban_duration)
                break

    def report_success(self, proxy_url: str) -> None:
        for p in self.proxies:
            if p.url == proxy_url:
                p.mark_success()
                break

    @property
    def available_count(self) -> int:
        return len(self._available())

    @property
    def total_count(self) -> int:
        return len(self.proxies)
