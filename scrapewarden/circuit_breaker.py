from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 30.0  # seconds before attempting recovery
    success_threshold: int = 2      # successes needed in HALF_OPEN to close


@dataclass
class CircuitBreaker:
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _success_count: int = field(default=0, init=False)
    _opened_at: Optional[float] = field(default=None, init=False)

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._opened_at >= self.config.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
        return self._state

    def allow_request(self) -> bool:
        """Returns True if the request should be allowed through."""
        return self.state != CircuitState.OPEN

    def record_success(self) -> None:
        """Record a successful request outcome."""
        state = self.state
        if state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._close()
        elif state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed request outcome."""
        state = self.state
        if state == CircuitState.HALF_OPEN:
            self._open()
        elif state == CircuitState.CLOSED:
            self._failure_count += 1
            if self._failure_count >= self.config.failure_threshold:
                self._open()

    def _open(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = time.monotonic()
        self._failure_count = 0
        self._success_count = 0

    def _close(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._opened_at = None

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        self._close()
