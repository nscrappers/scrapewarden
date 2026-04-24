from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class TimeoutConfig:
    default_timeout: float = 30.0
    connect_timeout: float = 10.0
    read_timeout: float = 20.0
    per_domain_timeouts: Dict[str, float] = field(default_factory=dict)
    backoff_on_timeout: bool = True
    backoff_multiplier: float = 1.5
    max_timeout: float = 120.0

    @classmethod
    def from_dict(cls, data: dict) -> "TimeoutConfig":
        return cls(
            default_timeout=data.get("default_timeout", 30.0),
            connect_timeout=data.get("connect_timeout", 10.0),
            read_timeout=data.get("read_timeout", 20.0),
            per_domain_timeouts=data.get("per_domain_timeouts", {}),
            backoff_on_timeout=data.get("backoff_on_timeout", True),
            backoff_multiplier=data.get("backoff_multiplier", 1.5),
            max_timeout=data.get("max_timeout", 120.0),
        )


class TimeoutManager:
    """Tracks per-domain timeouts and applies backoff after timeout events."""

    def __init__(self, config: Optional[TimeoutConfig] = None) -> None:
        self._config = config or TimeoutConfig()
        self._domain_timeouts: Dict[str, float] = {}
        self._timeout_counts: Dict[str, int] = {}
        self._last_timeout_at: Dict[str, float] = {}

    def get_timeout(self, domain: str) -> float:
        """Return the current effective timeout for a domain."""
        if domain in self._config.per_domain_timeouts:
            base = self._config.per_domain_timeouts[domain]
        else:
            base = self._config.default_timeout

        if self._config.backoff_on_timeout and domain in self._domain_timeouts:
            return self._domain_timeouts[domain]

        return base

    def get_connect_timeout(self, domain: str) -> float:
        """Return connect timeout, scaled proportionally if domain is backed off."""
        effective = self.get_timeout(domain)
        base = self._config.per_domain_timeouts.get(domain, self._config.default_timeout)
        scale = effective / base if base > 0 else 1.0
        return min(self._config.connect_timeout * scale, self._config.max_timeout)

    def record_timeout(self, domain: str) -> None:
        """Increase the timeout for a domain after a timeout event."""
        self._timeout_counts[domain] = self._timeout_counts.get(domain, 0) + 1
        self._last_timeout_at[domain] = time.monotonic()
        current = self._domain_timeouts.get(
            domain,
            self._config.per_domain_timeouts.get(domain, self._config.default_timeout),
        )
        backed_off = min(current * self._config.backoff_multiplier, self._config.max_timeout)
        self._domain_timeouts[domain] = backed_off

    def record_success(self, domain: str) -> None:
        """Reset the domain timeout to its base value after a successful request."""
        self._domain_timeouts.pop(domain, None)
        self._timeout_counts.pop(domain, None)
        self._last_timeout_at.pop(domain, None)

    def timeout_count(self, domain: str) -> int:
        return self._timeout_counts.get(domain, 0)

    def reset(self) -> None:
        self._domain_timeouts.clear()
        self._timeout_counts.clear()
        self._last_timeout_at.clear()
