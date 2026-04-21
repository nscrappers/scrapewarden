"""Request deduplication using fingerprints to avoid re-fetching seen URLs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Set

from scrapewarden.request_fingerprinter import FingerprintConfig, RequestFingerprinter


@dataclass
class DeduplicatorConfig:
    max_size: int = 100_000
    fingerprint: FingerprintConfig = field(default_factory=FingerprintConfig)

    @classmethod
    def from_dict(cls, data: dict) -> "DeduplicatorConfig":
        fp_cfg = FingerprintConfig.from_dict(data.get("fingerprint", {}))
        return cls(
            max_size=int(data.get("max_size", 100_000)),
            fingerprint=fp_cfg,
        )


class RequestDeduplicator:
    """Tracks seen request fingerprints and filters duplicates."""

    def __init__(self, config: Optional[DeduplicatorConfig] = None) -> None:
        self._config = config or DeduplicatorConfig()
        self._fingerprinter = RequestFingerprinter(self._config.fingerprint)
        self._seen: Set[str] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_seen(self, url: str, method: str = "GET", body: bytes = b"") -> bool:
        """Return True if this request has been seen before."""
        fp = self._fingerprinter.fingerprint(url, method=method, body=body)
        return fp in self._seen

    def mark_seen(
        self, url: str, method: str = "GET", body: bytes = b""
    ) -> str:
        """Record a request as seen. Returns the fingerprint."""
        fp = self._fingerprinter.fingerprint(url, method=method, body=body)
        if len(self._seen) >= self._config.max_size:
            # Evict an arbitrary entry to stay within the size cap.
            self._seen.pop()
        self._seen.add(fp)
        return fp

    def check_and_mark(
        self, url: str, method: str = "GET", body: bytes = b""
    ) -> bool:
        """Atomically check if seen and mark if not. Returns True if duplicate."""
        if self.is_seen(url, method=method, body=body):
            return True
        self.mark_seen(url, method=method, body=body)
        return False

    def clear(self) -> None:
        """Reset all seen fingerprints."""
        self._seen.clear()

    @property
    def size(self) -> int:
        """Number of currently tracked fingerprints."""
        return len(self._seen)
