"""Health monitoring for domains: tracks uptime, response times, and health scores."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional


@dataclass
class HealthConfig:
    window_size: int = 50          # number of recent requests to consider
    min_health_score: float = 0.4  # below this a domain is considered unhealthy
    response_time_threshold: float = 5.0  # seconds; above this counts as slow

    @classmethod
    def from_dict(cls, data: dict) -> "HealthConfig":
        return cls(
            window_size=data.get("window_size", 50),
            min_health_score=data.get("min_health_score", 0.4),
            response_time_threshold=data.get("response_time_threshold", 5.0),
        )


@dataclass
class _DomainHealth:
    successes: Deque[bool] = field(default_factory=lambda: deque(maxlen=50))
    response_times: Deque[float] = field(default_factory=lambda: deque(maxlen=50))
    last_seen: float = field(default_factory=time.monotonic)

    def record(self, success: bool, response_time: float) -> None:
        self.successes.append(success)
        self.response_times.append(response_time)
        self.last_seen = time.monotonic()

    def health_score(self) -> float:
        if not self.successes:
            return 1.0
        return sum(self.successes) / len(self.successes)

    def avg_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)

    def to_dict(self) -> dict:
        return {
            "health_score": round(self.health_score(), 4),
            "avg_response_time": round(self.avg_response_time(), 4),
            "sample_count": len(self.successes),
            "last_seen": self.last_seen,
        }


class HealthMonitor:
    def __init__(self, config: Optional[HealthConfig] = None) -> None:
        self.config = config or HealthConfig()
        self._domains: Dict[str, _DomainHealth] = {}

    def _get(self, domain: str) -> _DomainHealth:
        if domain not in self._domains:
            h = _DomainHealth(
                successes=deque(maxlen=self.config.window_size),
                response_times=deque(maxlen=self.config.window_size),
            )
            self._domains[domain] = h
        return self._domains[domain]

    def record(self, domain: str, success: bool, response_time: float) -> None:
        self._get(domain).record(success, response_time)

    def is_healthy(self, domain: str) -> bool:
        return self._get(domain).health_score() >= self.config.min_health_score

    def health_score(self, domain: str) -> float:
        return self._get(domain).health_score()

    def avg_response_time(self, domain: str) -> float:
        return self._get(domain).avg_response_time()

    def is_slow(self, domain: str) -> bool:
        return self.avg_response_time(domain) > self.config.response_time_threshold

    def domain_stats(self, domain: str) -> dict:
        return self._get(domain).to_dict()

    def all_stats(self) -> Dict[str, dict]:
        return {d: h.to_dict() for d, h in self._domains.items()}
