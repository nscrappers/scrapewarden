"""Header rotation utility for mimicking real browser traffic."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


DEFAULT_USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

DEFAULT_ACCEPT_LANGUAGES: List[str] = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.8",
    "en-US,en;q=0.8,es;q=0.6",
    "en-CA,en;q=0.9,fr-CA;q=0.7",
]


@dataclass
class HeaderRotatorConfig:
    user_agents: List[str] = field(default_factory=lambda: list(DEFAULT_USER_AGENTS))
    accept_languages: List[str] = field(default_factory=lambda: list(DEFAULT_ACCEPT_LANGUAGES))
    rotate_accept_language: bool = True
    extra_headers: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "HeaderRotatorConfig":
        return cls(
            user_agents=data.get("user_agents", list(DEFAULT_USER_AGENTS)),
            accept_languages=data.get("accept_languages", list(DEFAULT_ACCEPT_LANGUAGES)),
            rotate_accept_language=data.get("rotate_accept_language", True),
            extra_headers=data.get("extra_headers", {}),
        )


class HeaderRotator:
    """Randomly selects User-Agent and other headers to reduce fingerprinting."""

    def __init__(self, config: Optional[HeaderRotatorConfig] = None) -> None:
        self._config = config or HeaderRotatorConfig()

    def get_headers(self) -> Dict[str, str]:
        """Return a dict of HTTP headers with a rotated User-Agent."""
        headers: Dict[str, str] = {}

        if self._config.user_agents:
            headers["User-Agent"] = random.choice(self._config.user_agents)

        if self._config.rotate_accept_language and self._config.accept_languages:
            headers["Accept-Language"] = random.choice(self._config.accept_languages)

        headers.update(self._config.extra_headers)
        return headers

    def apply(self, existing: Dict[str, str]) -> Dict[str, str]:
        """Merge rotated headers into *existing*, without overwriting already-set keys."""
        rotated = self.get_headers()
        merged = {**rotated, **existing}
        return merged

    @property
    def user_agent_pool_size(self) -> int:
        return len(self._config.user_agents)
