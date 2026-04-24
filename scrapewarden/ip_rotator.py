"""IP rotation tracker for managing outbound IP addresses."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional
import random


@dataclass
class IPEntry:
    address: str
    failure_count: int = 0
    last_used: Optional[datetime] = None
    banned_until: Optional[datetime] = None

    def is_banned(self) -> bool:
        if self.banned_until is None:
            return False
        return datetime.utcnow() < self.banned_until

    def mark_failure(self, ban_duration_seconds: float = 60.0) -> None:
        self.failure_count += 1
        if self.failure_count >= 3:
            self.banned_until = datetime.utcnow() + timedelta(seconds=ban_duration_seconds)

    def mark_success(self) -> None:
        self.failure_count = 0
        self.banned_until = None


@dataclass
class IPRotatorConfig:
    ban_duration_seconds: float = 60.0
    strategy: str = "round_robin"  # round_robin | random

    @classmethod
    def from_dict(cls, data: dict) -> "IPRotatorConfig":
        return cls(
            ban_duration_seconds=float(data.get("ban_duration_seconds", 60.0)),
            strategy=data.get("strategy", "round_robin"),
        )


class IPRotator:
    def __init__(self, addresses: List[str], config: Optional[IPRotatorConfig] = None) -> None:
        self._config = config or IPRotatorConfig()
        self._entries: List[IPEntry] = [IPEntry(address=a) for a in addresses]
        self._index: int = 0

    def next_ip(self) -> Optional[str]:
        available = [e for e in self._entries if not e.is_banned()]
        if not available:
            return None
        if self._config.strategy == "random":
            entry = random.choice(available)
        else:
            self._index = self._index % len(available)
            entry = available[self._index]
            self._index = (self._index + 1) % len(available)
        entry.last_used = datetime.utcnow()
        return entry.address

    def report_failure(self, address: str) -> None:
        for entry in self._entries:
            if entry.address == address:
                entry.mark_failure(self._config.ban_duration_seconds)
                return

    def report_success(self, address: str) -> None:
        for entry in self._entries:
            if entry.address == address:
                entry.mark_success()
                return

    def available_count(self) -> int:
        return sum(1 for e in self._entries if not e.is_banned())

    def all_banned(self) -> bool:
        return self.available_count() == 0
