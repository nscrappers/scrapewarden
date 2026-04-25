"""User-agent pool with weighted selection and rotation tracking."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class UserAgentPoolConfig:
    agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    ])
    weights: Optional[List[float]] = None
    avoid_repeat: bool = True
    ban_on_consecutive_failures: int = 3

    @classmethod
    def from_dict(cls, data: dict) -> "UserAgentPoolConfig":
        return cls(
            agents=data.get("agents", cls.__dataclass_fields__["agents"].default_factory()),
            weights=data.get("weights"),
            avoid_repeat=data.get("avoid_repeat", True),
            ban_on_consecutive_failures=int(data.get("ban_on_consecutive_failures", 3)),
        )


@dataclass
class _AgentEntry:
    agent: str
    consecutive_failures: int = 0
    banned: bool = False

    def mark_failure(self, threshold: int) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= threshold:
            self.banned = True

    def mark_success(self) -> None:
        self.consecutive_failures = 0
        self.banned = False


class UserAgentPool:
    def __init__(self, config: Optional[UserAgentPoolConfig] = None) -> None:
        self._config = config or UserAgentPoolConfig()
        self._entries: List[_AgentEntry] = [
            _AgentEntry(a) for a in self._config.agents
        ]
        self._last_agent: Optional[str] = None
        self._usage_counts: Dict[str, int] = {a: 0 for a in self._config.agents}

    def pick(self) -> str:
        available = [
            e for e in self._entries
            if not e.banned and (
                not self._config.avoid_repeat or e.agent != self._last_agent or len(self._entries) == 1
            )
        ]
        if not available:
            available = [e for e in self._entries if not e.banned]
        if not available:
            available = self._entries  # all banned — fall back

        weights = None
        if self._config.weights and len(self._config.weights) == len(self._entries):
            idx_map = {e.agent: i for i, e in enumerate(self._entries)}
            weights = [self._config.weights[idx_map[e.agent]] for e in available]

        chosen = random.choices(available, weights=weights, k=1)[0]
        self._last_agent = chosen.agent
        self._usage_counts[chosen.agent] = self._usage_counts.get(chosen.agent, 0) + 1
        return chosen.agent

    def report_failure(self, agent: str) -> None:
        for entry in self._entries:
            if entry.agent == agent:
                entry.mark_failure(self._config.ban_on_consecutive_failures)
                break

    def report_success(self, agent: str) -> None:
        for entry in self._entries:
            if entry.agent == agent:
                entry.mark_success()
                break

    @property
    def active_count(self) -> int:
        return sum(1 for e in self._entries if not e.banned)

    @property
    def usage_counts(self) -> Dict[str, int]:
        return dict(self._usage_counts)
