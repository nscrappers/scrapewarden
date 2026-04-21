"""Request fingerprinting to detect and deduplicate duplicate scrape requests."""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, Optional, Set
from urllib.parse import urlparse, urlencode, parse_qsl


@dataclass
class FingerprintConfig:
    normalize_url: bool = True
    ignore_query_params: Set[str] = field(default_factory=set)
    include_headers: Set[str] = field(default_factory=set)
    hash_algorithm: str = "sha1"

    @classmethod
    def from_dict(cls, data: dict) -> "FingerprintConfig":
        return cls(
            normalize_url=data.get("normalize_url", True),
            ignore_query_params=set(data.get("ignore_query_params", [])),
            include_headers=set(h.lower() for h in data.get("include_headers", [])),
            hash_algorithm=data.get("hash_algorithm", "sha1"),
        )


class RequestFingerprinter:
    """Generates stable fingerprints for HTTP requests to detect duplicates."""

    def __init__(self, config: Optional[FingerprintConfig] = None):
        self.config = config or FingerprintConfig()
        self._seen: Set[str] = set()

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = re.sub(r"/+", "/", parsed.path) or "/"
        params = sorted(
            [
                (k, v)
                for k, v in parse_qsl(parsed.query)
                if k not in self.config.ignore_query_params
            ]
        )
        query = urlencode(params)
        return f"{scheme}://{netloc}{path}" + (f"?{query}" if query else "")

    def fingerprint(
        self,
        url: str,
        method: str = "GET",
        body: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        """Return a hex digest fingerprint for the given request."""
        h = hashlib.new(self.config.hash_algorithm)
        normalized = self._normalize_url(url) if self.config.normalize_url else url
        h.update(method.upper().encode())
        h.update(normalized.encode())
        if body:
            h.update(body)
        if headers and self.config.include_headers:
            for header_name in sorted(self.config.include_headers):
                value = headers.get(header_name) or headers.get(header_name.title(), "")
                h.update(f"{header_name}:{value}".encode())
        return h.hexdigest()

    def is_seen(self, fingerprint: str) -> bool:
        """Return True if this fingerprint has been seen before."""
        return fingerprint in self._seen

    def mark_seen(self, fingerprint: str) -> None:
        """Record a fingerprint as seen."""
        self._seen.add(fingerprint)

    def seen_count(self) -> int:
        return len(self._seen)

    def reset(self) -> None:
        """Clear all seen fingerprints."""
        self._seen.clear()
