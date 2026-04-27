"""Aggregated health statistics across all monitored domains."""
from __future__ import annotations

from typing import Dict, List, Optional

from .health_monitor import HealthMonitor


class HealthStats:
    """Provides aggregate views over a HealthMonitor instance."""

    def __init__(self, monitor: HealthMonitor) -> None:
        self._monitor = monitor

    def unhealthy_domains(self) -> List[str]:
        """Return domains whose health score is below the configured threshold."""
        return [
            domain
            for domain in self._monitor._domains
            if not self._monitor.is_healthy(domain)
        ]

    def slow_domains(self) -> List[str]:
        """Return domains whose average response time exceeds the threshold."""
        return [
            domain
            for domain in self._monitor._domains
            if self._monitor.is_slow(domain)
        ]

    def top_n_by_health(self, n: int = 5) -> List[Dict]:
        """Return the top-N healthiest domains sorted by health score desc."""
        items = [
            {"domain": d, **self._monitor.domain_stats(d)}
            for d in self._monitor._domains
        ]
        return sorted(items, key=lambda x: x["health_score"], reverse=True)[:n]

    def worst_n_by_health(self, n: int = 5) -> List[Dict]:
        """Return the N least-healthy domains sorted by health score asc."""
        items = [
            {"domain": d, **self._monitor.domain_stats(d)}
            for d in self._monitor._domains
        ]
        return sorted(items, key=lambda x: x["health_score"])[:n]

    def summary(self) -> Dict:
        all_stats = self._monitor.all_stats()
        if not all_stats:
            return {"total_domains": 0, "unhealthy": 0, "slow": 0}
        scores = [v["health_score"] for v in all_stats.values()]
        return {
            "total_domains": len(all_stats),
            "unhealthy": len(self.unhealthy_domains()),
            "slow": len(self.slow_domains()),
            "avg_health_score": round(sum(scores) / len(scores), 4),
            "min_health_score": round(min(scores), 4),
            "max_health_score": round(max(scores), 4),
        }
