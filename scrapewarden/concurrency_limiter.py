"""Per-domain concurrency limiting using asyncio semaphores."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Dict, Optional


@dataclass
class ConcurrencyConfig:
    max_concurrent_per_domain: int = 4
    global_max_concurrent: int = 16

    @classmethod
    def from_dict(cls, data: dict) -> "ConcurrencyConfig":
        return cls(
            max_concurrent_per_domain=int(data.get("max_concurrent_per_domain", 4)),
            global_max_concurrent=int(data.get("global_max_concurrent", 16)),
        )


class ConcurrencyLimiter:
    """Limits concurrent requests both globally and per domain."""

    def __init__(self, config: Optional[ConcurrencyConfig] = None) -> None:
        self._config = config or ConcurrencyConfig()
        self._global_sem = asyncio.Semaphore(self._config.global_max_concurrent)
        self._domain_sems: Dict[str, asyncio.Semaphore] = {}

    def _domain_sem(self, domain: str) -> asyncio.Semaphore:
        if domain not in self._domain_sems:
            self._domain_sems[domain] = asyncio.Semaphore(
                self._config.max_concurrent_per_domain
            )
        return self._domain_sems[domain]

    @asynccontextmanager
    async def acquire(self, domain: str) -> AsyncIterator[None]:
        """Async context manager that acquires both global and domain slots."""
        async with self._global_sem:
            async with self._domain_sem(domain):
                yield

    def global_available(self) -> int:
        return self._global_sem._value  # type: ignore[attr-defined]

    def domain_available(self, domain: str) -> int:
        sem = self._domain_sems.get(domain)
        if sem is None:
            return self._config.max_concurrent_per_domain
        return sem._value  # type: ignore[attr-defined]

    def known_domains(self) -> list:
        return list(self._domain_sems.keys())
