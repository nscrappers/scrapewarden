"""Tag outgoing requests with metadata labels for tracking and filtering."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TaggerConfig:
    """Configuration for the RequestTagger."""
    default_tags: Dict[str, str] = field(default_factory=dict)
    domain_tags: Dict[str, Dict[str, str]] = field(default_factory=dict)
    tag_header: str = "X-ScrapeWarden-Tags"
    include_in_headers: bool = True
    max_tags_per_request: int = 20

    @classmethod
    def from_dict(cls, data: dict) -> "TaggerConfig":
        return cls(
            default_tags=data.get("default_tags", {}),
            domain_tags=data.get("domain_tags", {}),
            tag_header=data.get("tag_header", "X-ScrapeWarden-Tags"),
            include_in_headers=data.get("include_in_headers", True),
            max_tags_per_request=data.get("max_tags_per_request", 20),
        )


class RequestTagger:
    """Attaches key-value tag metadata to requests."""

    def __init__(self, config: Optional[TaggerConfig] = None) -> None:
        self.config = config or TaggerConfig()
        self._request_tags: Dict[str, Dict[str, str]] = {}

    def tag_request(self, request_id: str, domain: str, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Compute and store tags for a request, returning the merged tag dict."""
        tags: Dict[str, str] = {}
        tags.update(self.config.default_tags)
        if domain in self.config.domain_tags:
            tags.update(self.config.domain_tags[domain])
        if extra:
            tags.update(extra)
        # Enforce max tags limit
        if len(tags) > self.config.max_tags_per_request:
            keys = list(tags.keys())[:self.config.max_tags_per_request]
            tags = {k: tags[k] for k in keys}
        self._request_tags[request_id] = tags
        return tags

    def get_tags(self, request_id: str) -> Dict[str, str]:
        """Retrieve stored tags for a given request ID."""
        return self._request_tags.get(request_id, {})

    def build_header(self, tags: Dict[str, str]) -> str:
        """Serialise tags as a comma-separated key=value header value."""
        return ",".join(f"{k}={v}" for k, v in tags.items())

    def clear(self, request_id: str) -> None:
        """Remove stored tags for a completed request."""
        self._request_tags.pop(request_id, None)

    @property
    def tracked_count(self) -> int:
        return len(self._request_tags)
