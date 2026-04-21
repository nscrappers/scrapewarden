from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlparse


@dataclass
class RedirectConfig:
    max_redirects: int = 10
    track_history: bool = True
    allow_cross_domain: bool = True
    blocked_schemes: List[str] = field(default_factory=lambda: ["file", "ftp"])

    @classmethod
    def from_dict(cls, data: dict) -> "RedirectConfig":
        return cls(
            max_redirects=data.get("max_redirects", 10),
            track_history=data.get("track_history", True),
            allow_cross_domain=data.get("allow_cross_domain", True),
            blocked_schemes=data.get("blocked_schemes", ["file", "ftp"]),
        )


@dataclass
class RedirectChain:
    urls: List[str] = field(default_factory=list)

    def add(self, url: str) -> None:
        self.urls.append(url)

    @property
    def count(self) -> int:
        return max(0, len(self.urls) - 1)

    @property
    def origin(self) -> Optional[str]:
        return self.urls[0] if self.urls else None

    @property
    def final(self) -> Optional[str]:
        return self.urls[-1] if self.urls else None

    def crossed_domain(self) -> bool:
        if len(self.urls) < 2:
            return False
        origin_host = urlparse(self.urls[0]).netloc
        return any(urlparse(u).netloc != origin_host for u in self.urls[1:])


class RedirectTracker:
    def __init__(self, config: Optional[RedirectConfig] = None) -> None:
        self.config = config or RedirectConfig()
        self._chains: dict[str, RedirectChain] = {}

    def start(self, request_id: str, url: str) -> RedirectChain:
        chain = RedirectChain()
        chain.add(url)
        self._chains[request_id] = chain
        return chain

    def record(self, request_id: str, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme in self.config.blocked_schemes:
            raise ValueError(f"Blocked redirect scheme '{parsed.scheme}' in URL: {url}")
        chain = self._chains.get(request_id)
        if chain is None:
            chain = self.start(request_id, url)
            return
        if chain.count >= self.config.max_redirects:
            raise TooManyRedirectsError(
                f"Exceeded max redirects ({self.config.max_redirects}) for {chain.origin}"
            )
        if not self.config.allow_cross_domain and chain.origin:
            origin_host = urlparse(chain.origin).netloc
            if urlparse(url).netloc != origin_host:
                raise CrossDomainRedirectError(
                    f"Cross-domain redirect blocked: {chain.origin} -> {url}"
                )
        chain.add(url)

    def get(self, request_id: str) -> Optional[RedirectChain]:
        return self._chains.get(request_id)

    def clear(self, request_id: str) -> None:
        self._chains.pop(request_id, None)


class TooManyRedirectsError(Exception):
    pass


class CrossDomainRedirectError(Exception):
    pass
