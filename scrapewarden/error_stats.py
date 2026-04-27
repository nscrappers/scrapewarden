"""Per-domain error statistics collected by the error classifier middleware."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict

from scrapewarden.error_classifier import ErrorClass


@dataclass
class _DomainErrorStats:
    counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    total: int = 0

    def record(self, error_class: ErrorClass) -> None:
        self.counts[error_class.value] += 1
        self.total += 1

    def rate(self, error_class: ErrorClass) -> float:
        if self.total == 0:
            return 0.0
        return self.counts[error_class.value] / self.total

    def to_dict(self) -> Dict:
        return {
            "total": self.total,
            "counts": dict(self.counts),
            "rates": {
                ec.value: self.rate(ec) for ec in ErrorClass
            },
        }


class ErrorStats:
    def __init__(self) -> None:
        self._domains: Dict[str, _DomainErrorStats] = defaultdict(_DomainErrorStats)

    def record(self, domain: str, error_class: ErrorClass) -> None:
        self._domains[domain].record(error_class)

    def for_domain(self, domain: str) -> _DomainErrorStats:
        return self._domains[domain]

    def total_for_domain(self, domain: str) -> int:
        return self._domains[domain].total

    def rate_for_domain(self, domain: str, error_class: ErrorClass) -> float:
        return self._domains[domain].rate(error_class)

    def to_dict(self) -> Dict:
        return {domain: stats.to_dict() for domain, stats in self._domains.items()}

    def reset(self, domain: Optional[str] = None) -> None:  # type: ignore[name-defined]
        if domain:
            self._domains.pop(domain, None)
        else:
            self._domains.clear()
