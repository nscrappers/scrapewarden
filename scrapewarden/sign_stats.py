"""Statistics tracking for request signing activity."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class _DomainSignStats:
    signed: int = 0
    verified_ok: int = 0
    verified_fail: int = 0

    @property
    def verification_failure_rate(self) -> float:
        total = self.verified_ok + self.verified_fail
        return self.verified_fail / total if total > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "signed": self.signed,
            "verified_ok": self.verified_ok,
            "verified_fail": self.verified_fail,
            "verification_failure_rate": round(self.verification_failure_rate, 4),
        }


class SignStats:
    """Collects per-domain signing statistics."""

    def __init__(self) -> None:
        self._domains: Dict[str, _DomainSignStats] = {}

    def _get(self, domain: str) -> _DomainSignStats:
        if domain not in self._domains:
            self._domains[domain] = _DomainSignStats()
        return self._domains[domain]

    def record_signed(self, domain: str) -> None:
        self._get(domain).signed += 1

    def record_verified(self, domain: str, success: bool) -> None:
        stats = self._get(domain)
        if success:
            stats.verified_ok += 1
        else:
            stats.verified_fail += 1

    def for_domain(self, domain: str) -> dict:
        return self._get(domain).to_dict()

    def all(self) -> Dict[str, dict]:
        return {d: s.to_dict() for d, s in self._domains.items()}

    def reset(self, domain: Optional[str] = None) -> None:  # type: ignore[name-defined]
        if domain:
            self._domains.pop(domain, None)
        else:
            self._domains.clear()
