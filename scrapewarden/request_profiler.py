"""Request profiling: tracks timing and size metrics per domain."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional, Tuple


@dataclass
class ProfilerConfig:
    enabled: bool = True
    window_size: int = 100  # number of recent requests to keep per domain
    slow_threshold_seconds: float = 3.0

    @classmethod
    def from_dict(cls, data: dict) -> "ProfilerConfig":
        return cls(
            enabled=data.get("enabled", True),
            window_size=int(data.get("window_size", 100)),
            slow_threshold_seconds=float(data.get("slow_threshold_seconds", 3.0)),
        )


@dataclass
class _RequestSample:
    elapsed: float
    request_bytes: int
    response_bytes: int
    status_code: int
    timestamp: float = field(default_factory=time.monotonic)


class _DomainProfile:
    def __init__(self, window_size: int, slow_threshold: float) -> None:
        self._window: Deque[_RequestSample] = deque(maxlen=window_size)
        self._slow_threshold = slow_threshold

    def record(self, elapsed: float, req_bytes: int, resp_bytes: int, status: int) -> None:
        self._window.append(_RequestSample(elapsed, req_bytes, resp_bytes, status))

    def avg_elapsed(self) -> float:
        if not self._window:
            return 0.0
        return sum(s.elapsed for s in self._window) / len(self._window)

    def slow_request_rate(self) -> float:
        if not self._window:
            return 0.0
        slow = sum(1 for s in self._window if s.elapsed >= self._slow_threshold)
        return slow / len(self._window)

    def total_bytes(self) -> Tuple[int, int]:
        req = sum(s.request_bytes for s in self._window)
        resp = sum(s.response_bytes for s in self._window)
        return req, resp

    def to_dict(self) -> dict:
        req_b, resp_b = self.total_bytes()
        return {
            "sample_count": len(self._window),
            "avg_elapsed_seconds": round(self.avg_elapsed(), 4),
            "slow_request_rate": round(self.slow_request_rate(), 4),
            "total_request_bytes": req_b,
            "total_response_bytes": resp_b,
        }


class RequestProfiler:
    def __init__(self, config: Optional[ProfilerConfig] = None) -> None:
        self.config = config or ProfilerConfig()
        self._profiles: Dict[str, _DomainProfile] = defaultdict(
            lambda: _DomainProfile(self.config.window_size, self.config.slow_threshold_seconds)
        )

    def record(self, domain: str, elapsed: float, req_bytes: int, resp_bytes: int, status: int) -> None:
        if not self.config.enabled:
            return
        self._profiles[domain].record(elapsed, req_bytes, resp_bytes, status)

    def profile(self, domain: str) -> dict:
        if domain not in self._profiles:
            return {}
        return self._profiles[domain].to_dict()

    def all_profiles(self) -> Dict[str, dict]:
        return {d: p.to_dict() for d, p in self._profiles.items()}

    def slow_domains(self, threshold: Optional[float] = None) -> list:
        t = threshold or self.config.slow_threshold_seconds
        return [
            d for d, p in self._profiles.items()
            if p.avg_elapsed() >= t
        ]
