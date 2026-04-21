"""Backoff strategy implementations for retry delays."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BackoffType(str, Enum):
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    JITTERED = "jittered"


@dataclass
class BackoffConfig:
    strategy: BackoffType = BackoffType.EXPONENTIAL
    base_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter_range: float = 0.5
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "BackoffConfig":
        strategy = BackoffType(data.get("strategy", BackoffType.EXPONENTIAL))
        return cls(
            strategy=strategy,
            base_delay=float(data.get("base_delay", 1.0)),
            max_delay=float(data.get("max_delay", 60.0)),
            multiplier=float(data.get("multiplier", 2.0)),
            jitter_range=float(data.get("jitter_range", 0.5)),
        )


class BackoffStrategy:
    """Calculates delay durations based on retry attempt number."""

    def __init__(self, config: Optional[BackoffConfig] = None) -> None:
        self.config = config or BackoffConfig()

    def delay_for(self, attempt: int) -> float:
        """Return delay in seconds for the given attempt (0-indexed)."""
        cfg = self.config
        strategy = cfg.strategy

        if strategy == BackoffType.FIXED:
            delay = cfg.base_delay

        elif strategy == BackoffType.LINEAR:
            delay = cfg.base_delay * (attempt + 1)

        elif strategy == BackoffType.EXPONENTIAL:
            delay = cfg.base_delay * (cfg.multiplier ** attempt)

        elif strategy == BackoffType.JITTERED:
            exp_delay = cfg.base_delay * (cfg.multiplier ** attempt)
            jitter = random.uniform(-cfg.jitter_range, cfg.jitter_range) * exp_delay
            delay = exp_delay + jitter

        else:
            delay = cfg.base_delay

        return max(0.0, min(delay, cfg.max_delay))

    def delays(self, max_attempts: int) -> list[float]:
        """Return list of delays for all attempts up to max_attempts."""
        return [self.delay_for(i) for i in range(max_attempts)]
