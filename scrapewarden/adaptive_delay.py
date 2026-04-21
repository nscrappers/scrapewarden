"""Adaptive delay manager that adjusts wait times based on domain response signals."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from scrapewarden.backoff_strategy import BackoffConfig, BackoffStrategy, BackoffType


@dataclass
class AdaptiveDelayConfig:
    min_delay: float = 0.5
    max_delay: float = 30.0
    increase_factor: float = 1.5
    decrease_factor: float = 0.9
    soft_block_boost: float = 3.0
    backoff: BackoffConfig = field(default_factory=BackoffConfig)

    @classmethod
    def from_dict(cls, data: dict) -> "AdaptiveDelayConfig":
        backoff_data = data.get("backoff", {})
        return cls(
            min_delay=float(data.get("min_delay", 0.5)),
            max_delay=float(data.get("max_delay", 30.0)),
            increase_factor=float(data.get("increase_factor", 1.5)),
            decrease_factor=float(data.get("decrease_factor", 0.9)),
            soft_block_boost=float(data.get("soft_block_boost", 3.0)),
            backoff=BackoffConfig.from_dict(backoff_data),
        )


class AdaptiveDelayManager:
    """Tracks per-domain delays and adjusts them based on success/failure signals."""

    def __init__(self, config: Optional[AdaptiveDelayConfig] = None) -> None:
        self.config = config or AdaptiveDelayConfig()
        self._delays: Dict[str, float] = {}
        self._backoff = BackoffStrategy(self.config.backoff)

    def current_delay(self, domain: str) -> float:
        return self._delays.get(domain, self.config.min_delay)

    def record_success(self, domain: str) -> None:
        """Gradually reduce delay after a successful response."""
        current = self.current_delay(domain)
        new_delay = max(self.config.min_delay, current * self.config.decrease_factor)
        self._delays[domain] = new_delay

    def record_failure(self, domain: str, attempt: int = 0) -> None:
        """Increase delay after a failure, optionally using backoff for attempt count."""
        current = self.current_delay(domain)
        backoff_delay = self._backoff.delay_for(attempt)
        new_delay = min(self.config.max_delay, max(current * self.config.increase_factor, backoff_delay))
        self._delays[domain] = new_delay

    def record_soft_block(self, domain: str) -> None:
        """Apply a larger penalty delay on soft block (e.g. 429 response)."""
        current = self.current_delay(domain)
        new_delay = min(self.config.max_delay, current * self.config.soft_block_boost)
        self._delays[domain] = new_delay

    def reset(self, domain: str) -> None:
        """Reset delay for a domain back to minimum."""
        self._delays.pop(domain, None)

    def all_delays(self) -> Dict[str, float]:
        return dict(self._delays)
