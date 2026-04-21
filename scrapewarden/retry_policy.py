"""Retry policy with exponential backoff for scrapewarden."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Container, Optional


@dataclass
class RetryPolicyConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    retry_on_status: tuple[int, ...] = (429, 500, 502, 503, 504)


@dataclass
class RetryState:
    attempts: int = 0
    last_status: Optional[int] = None
    total_wait: float = 0.0

    def increment(self) -> None:
        self.attempts += 1

    @property
    def exhausted(self) -> bool:
        return False  # determined externally via policy


class RetryPolicy:
    """Calculates retry delays using exponential backoff with optional jitter."""

    def __init__(self, config: Optional[RetryPolicyConfig] = None) -> None:
        self.config = config or RetryPolicyConfig()

    def should_retry(self, state: RetryState, status_code: Optional[int] = None) -> bool:
        """Return True if another retry attempt is permitted."""
        if state.attempts >= self.config.max_retries:
            return False
        if status_code is not None and status_code not in self.config.retry_on_status:
            return False
        return True

    def next_delay(self, state: RetryState) -> float:
        """Compute the delay (seconds) before the next retry attempt."""
        delay = min(
            self.config.base_delay * (self.config.backoff_factor ** state.attempts),
            self.config.max_delay,
        )
        if self.config.jitter:
            delay *= 0.5 + random.random() * 0.5
        return delay

    def record_attempt(
        self,
        state: RetryState,
        status_code: Optional[int] = None,
        *,
        sleep: bool = False,
    ) -> float:
        """Increment attempt counter, optionally sleep, and return the delay used."""
        delay = self.next_delay(state)
        state.last_status = status_code
        state.attempts += 1
        state.total_wait += delay
        if sleep:
            time.sleep(delay)
        return delay
