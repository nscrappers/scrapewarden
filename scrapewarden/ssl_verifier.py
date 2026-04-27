"""SSL certificate verification and pinning support for scrapewarden."""
from __future__ import annotations

import hashlib
import ssl
import socket
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SSLVerifierConfig:
    enabled: bool = True
    pin_certificates: bool = False
    pinned_fingerprints: Dict[str, List[str]] = field(default_factory=dict)
    verify_hostname: bool = True
    min_tls_version: str = "TLSv1.2"
    timeout: float = 10.0

    @classmethod
    def from_dict(cls, data: dict) -> "SSLVerifierConfig":
        return cls(
            enabled=data.get("enabled", True),
            pin_certificates=data.get("pin_certificates", False),
            pinned_fingerprints=data.get("pinned_fingerprints", {}),
            verify_hostname=data.get("verify_hostname", True),
            min_tls_version=data.get("min_tls_version", "TLSv1.2"),
            timeout=float(data.get("timeout", 10.0)),
        )


@dataclass
class SSLVerificationResult:
    domain: str
    verified: bool
    fingerprint: Optional[str] = None
    error: Optional[str] = None
    tls_version: Optional[str] = None


class SSLVerifier:
    def __init__(self, config: SSLVerifierConfig) -> None:
        self.config = config
        self._cache: Dict[str, SSLVerificationResult] = {}

    def _get_cert_fingerprint(self, domain: str) -> Optional[str]:
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=self.config.timeout) as sock:
                with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert_der = ssock.getpeercert(binary_form=True)
                    if cert_der is None:
                        return None
                    return hashlib.sha256(cert_der).hexdigest()
        except Exception:
            return None

    def verify(self, domain: str) -> SSLVerificationResult:
        if not self.config.enabled:
            return SSLVerificationResult(domain=domain, verified=True)

        if domain in self._cache:
            return self._cache[domain]

        fingerprint = self._get_cert_fingerprint(domain)
        if fingerprint is None:
            result = SSLVerificationResult(
                domain=domain, verified=False, error="Could not retrieve certificate"
            )
            self._cache[domain] = result
            return result

        if self.config.pin_certificates:
            allowed = self.config.pinned_fingerprints.get(domain, [])
            if allowed and fingerprint not in allowed:
                result = SSLVerificationResult(
                    domain=domain,
                    verified=False,
                    fingerprint=fingerprint,
                    error="Certificate fingerprint not in pinned list",
                )
                self._cache[domain] = result
                return result

        result = SSLVerificationResult(domain=domain, verified=True, fingerprint=fingerprint)
        self._cache[domain] = result
        return result

    def clear_cache(self) -> None:
        self._cache.clear()

    def is_verified(self, domain: str) -> bool:
        return self.verify(domain).verified
