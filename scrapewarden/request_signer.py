"""Request signing utilities for HMAC-based request authentication."""
from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class SignerConfig:
    secret_key: str = ""
    algorithm: str = "sha256"
    include_timestamp: bool = True
    timestamp_header: str = "X-Timestamp"
    signature_header: str = "X-Signature"
    extra_headers_to_sign: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "SignerConfig":
        return cls(
            secret_key=data.get("secret_key", ""),
            algorithm=data.get("algorithm", "sha256"),
            include_timestamp=data.get("include_timestamp", True),
            timestamp_header=data.get("timestamp_header", "X-Timestamp"),
            signature_header=data.get("signature_header", "X-Signature"),
            extra_headers_to_sign=data.get("extra_headers_to_sign", []),
        )


class RequestSigner:
    """Signs outgoing requests using HMAC."""

    def __init__(self, config: SignerConfig) -> None:
        self._config = config

    def sign(self, method: str, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Return a dict of headers to add/merge into the request."""
        headers = dict(headers or {})
        timestamp = str(int(time.time()))

        parts = [method.upper(), url]
        if self._config.include_timestamp:
            parts.append(timestamp)
        for h in self._config.extra_headers_to_sign:
            parts.append(headers.get(h, ""))

        message = "\n".join(parts).encode()
        sig = hmac.new(
            self._config.secret_key.encode(),
            message,
            getattr(hashlib, self._config.algorithm),
        ).hexdigest()

        result: Dict[str, str] = {self._config.signature_header: sig}
        if self._config.include_timestamp:
            result[self._config.timestamp_header] = timestamp
        return result

    def verify(self, method: str, url: str, headers: Dict[str, str]) -> bool:
        """Verify a signed request. Returns True if valid."""
        if not self._config.secret_key:
            return False
        provided_sig = headers.get(self._config.signature_header, "")
        timestamp = headers.get(self._config.timestamp_header, "") if self._config.include_timestamp else ""

        parts = [method.upper(), url]
        if self._config.include_timestamp:
            parts.append(timestamp)
        for h in self._config.extra_headers_to_sign:
            parts.append(headers.get(h, ""))

        message = "\n".join(parts).encode()
        expected = hmac.new(
            self._config.secret_key.encode(),
            message,
            getattr(hashlib, self._config.algorithm),
        ).hexdigest()
        return hmac.compare_digest(provided_sig, expected)
