"""User-agent rotation statistics tracker.

Tracks per-domain and per-agent performance metrics to support
adaptive user-agent selection in UAMiddleware.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional


@dataclass
class _AgentStats:
    """Statistics for a single user-agent string."""

    requests: int = 0
    successes: int = 0
    failures: int = 0
    blocks: int = 0  # 403 / 429 responses attributed to this agent

    @property
    def failure_rate(self) -> float:
        """Fraction of requests that resulted in a failure."""
        if self.requests == 0:
            return 0.0
        return self.failures / self.requests

    @property
    def block_rate(self) -> float:
        """Fraction of requests that were blocked."""
        if self.requests == 0:
            return 0.0
        return self.blocks / self.requests

    def to_dict(self) -> dict:
        return {
            "requests": self.requests,
            "successes": self.successes,
            "failures": self.failures,
            "blocks": self.blocks,
            "failure_rate": round(self.failure_rate, 4),
            "block_rate": round(self.block_rate, 4),
        }


@dataclass
class _DomainAgentStats:
    """Aggregated user-agent statistics for a single domain."""

    total_requests: int = 0
    agents: Dict[str, _AgentStats] = field(default_factory=dict)

    def record(self, agent: str, *, success: bool, blocked: bool) -> None:
        if agent not in self.agents:
            self.agents[agent] = _AgentStats()
        entry = self.agents[agent]
        entry.requests += 1
        self.total_requests += 1
        if blocked:
            entry.blocks += 1
            entry.failures += 1
        elif success:
            entry.successes += 1
        else:
            entry.failures += 1

    def best_agent(self) -> Optional[str]:
        """Return the agent with the lowest block rate (min 1 request)."""
        candidates = {a: s for a, s in self.agents.items() if s.requests > 0}
        if not candidates:
            return None
        return min(candidates, key=lambda a: candidates[a].block_rate)

    def to_dict(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "agents": {a: s.to_dict() for a, s in self.agents.items()},
        }


class UAStats:
    """Thread-safe collector for user-agent rotation statistics."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._domains: Dict[str, _DomainAgentStats] = {}

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def record(
        self,
        domain: str,
        agent: str,
        *,
        success: bool = True,
        blocked: bool = False,
    ) -> None:
        """Record the outcome of a request made with *agent* on *domain*."""
        with self._lock:
            if domain not in self._domains:
                self._domains[domain] = _DomainAgentStats()
            self._domains[domain].record(agent, success=success, blocked=blocked)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def best_agent(self, domain: str) -> Optional[str]:
        """Return the best-performing agent for *domain*, or None."""
        with self._lock:
            entry = self._domains.get(domain)
            return entry.best_agent() if entry else None

    def agent_stats(self, domain: str, agent: str) -> Optional[_AgentStats]:
        """Return raw stats for a specific *agent* on *domain*."""
        with self._lock:
            domain_entry = self._domains.get(domain)
            if domain_entry is None:
                return None
            return domain_entry.agents.get(agent)

    def domain_summary(self, domain: str) -> Optional[dict]:
        """Return a serialisable summary for *domain*."""
        with self._lock:
            entry = self._domains.get(domain)
            return entry.to_dict() if entry else None

    def to_dict(self) -> dict:
        """Return a full serialisable snapshot of all collected stats."""
        with self._lock:
            return {d: s.to_dict() for d, s in self._domains.items()}

    def reset(self) -> None:
        """Clear all collected statistics."""
        with self._lock:
            self._domains.clear()
