"""Middleware that automatically signs outgoing requests."""
from __future__ import annotations

from typing import Dict, Optional

from .request_signer import RequestSigner, SignerConfig


class SignMiddleware:
    """Attaches HMAC signatures to requests before they are sent."""

    def __init__(self, signer: RequestSigner) -> None:
        self._signer = signer
        self._signed_count: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "SignMiddleware":
        config = SignerConfig.from_dict(data)
        return cls(RequestSigner(config))

    def on_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Return merged headers including signature headers."""
        headers = dict(headers or {})
        sig_headers = self._signer.sign(method, url, headers)
        headers.update(sig_headers)
        self._signed_count += 1
        return headers

    def verify_response_headers(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
    ) -> bool:
        """Optionally verify that a response carries a valid signature."""
        return self._signer.verify(method, url, headers)

    @property
    def signed_count(self) -> int:
        return self._signed_count

    def reset(self) -> None:
        self._signed_count = 0
