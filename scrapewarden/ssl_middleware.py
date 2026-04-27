"""Middleware that enforces SSL verification before requests are dispatched."""
from __future__ import annotations

from typing import Dict, List, Optional

from .ssl_verifier import SSLVerifier, SSLVerifierConfig, SSLVerificationResult


class SSLMiddleware:
    def __init__(self, config: Optional[SSLVerifierConfig] = None) -> None:
        self.config = config or SSLVerifierConfig()
        self._verifier = SSLVerifier(self.config)
        self._blocked: List[str] = []
        self._results: Dict[str, SSLVerificationResult] = {}

    @classmethod
    def from_dict(cls, data: dict) -> "SSLMiddleware":
        return cls(config=SSLVerifierConfig.from_dict(data))

    def on_request(self, domain: str) -> bool:
        """Returns True if the request should proceed, False if it should be blocked."""
        if not self.config.enabled:
            return True

        result = self._verifier.verify(domain)
        self._results[domain] = result

        if not result.verified:
            if domain not in self._blocked:
                self._blocked.append(domain)
            return False

        return True

    @property
    def blocked_domains(self) -> List[str]:
        return list(self._blocked)

    def last_result(self, domain: str) -> Optional[SSLVerificationResult]:
        return self._results.get(domain)

    def reset(self) -> None:
        self._blocked.clear()
        self._results.clear()
        self._verifier.clear_cache()

    @property
    def block_count(self) -> int:
        return len(self._blocked)
