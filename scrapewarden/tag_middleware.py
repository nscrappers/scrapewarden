"""Middleware that applies request tags and optionally injects them as headers."""
from __future__ import annotations

from typing import Dict, Optional

from .request_tagger import RequestTagger, TaggerConfig


class TagMiddleware:
    """Attach metadata tags to requests and expose tag data for downstream use."""

    def __init__(self, tagger: Optional[RequestTagger] = None) -> None:
        self.tagger = tagger or RequestTagger()
        self._tagged: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "TagMiddleware":
        config = TaggerConfig.from_dict(data)
        return cls(tagger=RequestTagger(config=config))

    def on_request(
        self,
        request_id: str,
        domain: str,
        headers: Dict[str, str],
        extra_tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Tag the request and, if configured, inject tags into headers.

        Returns the final headers dict (possibly augmented).
        """
        tags = self.tagger.tag_request(request_id, domain, extra=extra_tags)
        if self.tagger.config.include_in_headers and tags:
            headers = dict(headers)
            headers[self.tagger.config.tag_header] = self.tagger.build_header(tags)
        self._tagged += 1
        return headers

    def on_response(self, request_id: str) -> None:
        """Clean up stored tags once the response has been handled."""
        self.tagger.clear(request_id)

    @property
    def tagged_count(self) -> int:
        """Total number of requests tagged since instantiation."""
        return self._tagged

    @property
    def pending_count(self) -> int:
        """Number of requests whose tags have not yet been cleared."""
        return self.tagger.tracked_count
