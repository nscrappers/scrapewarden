"""Session tracking for per-domain request history and statistics."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional


@dataclass
class SessionConfig:
    window_seconds: float = 60.0
    max_history: int = 200

    @classmethod
    def from_dict(cls, data: dict) -> "SessionConfig":
        return cls(
            window_seconds=float(data.get("window_seconds", 60.0)),
            max_history=int(data.get("max_history", 200)),
        )


@dataclass
class DomainSession:
    domain: str
    config: SessionConfig
    _timestamps: Deque[float] = field(default_factory=deque)
    _success_count: int = 0
    _failure_count: int = 0
    _last_seen: Optional[float] = None

    def record_request(self, success: bool, ts: Optional[float] = None) -> None:
        now = ts if ts is not None else time.monotonic()
        self._timestamps.append(now)
        if len(self._timestamps) > self.config.max_history:
            self._timestamps.popleft()
        if success:
            self._success_count += 1
        else:
            self._failure_count += 1
        self._last_seen = now

    def recent_request_count(self, ts: Optional[float] = None) -> int:
        now = ts if ts is not None else time.monotonic()
        cutoff = now - self.config.window_seconds
        return sum(1 for t in self._timestamps if t >= cutoff)

    @property
    def total_requests(self) -> int:
        return self._success_count + self._failure_count

    @property
    def failure_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self._failure_count / self.total_requests

    @property
    def last_seen(self) -> Optional[float]:
        return self._last_seen


class SessionTracker:
    def __init__(self, config: Optional[SessionConfig] = None) -> None:
        self._config = config or SessionConfig()
        self._sessions: Dict[str, DomainSession] = {}

    def get_or_create(self, domain: str) -> DomainSession:
        if domain not in self._sessions:
            self._sessions[domain] = DomainSession(domain=domain, config=self._config)
        return self._sessions[domain]

    def record(self, domain: str, success: bool, ts: Optional[float] = None) -> None:
        self.get_or_create(domain).record_request(success, ts)

    def recent_count(self, domain: str, ts: Optional[float] = None) -> int:
        if domain not in self._sessions:
            return 0
        return self._sessions[domain].recent_request_count(ts)

    def failure_rate(self, domain: str) -> float:
        if domain not in self._sessions:
            return 0.0
        return self._sessions[domain].failure_rate

    def known_domains(self) -> list:
        return list(self._sessions.keys())

    def reset(self, domain: str) -> None:
        self._sessions.pop(domain, None)

    def summary(self, domain: str) -> Dict[str, object]:
        """Return a summary dict of statistics for the given domain.

        Returns an empty dict if the domain has not been seen.
        """
        if domain not in self._sessions:
            return {}
        session = self._sessions[domain]
        return {
            "domain": domain,
            "total_requests": session.total_requests,
            "failure_rate": session.failure_rate,
            "recent_requests": session.recent_request_count(),
            "last_seen": session.last_seen,
        }
