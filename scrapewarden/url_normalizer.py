"""URL normalization utilities for consistent request deduplication and caching."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import (
    ParseResult,
    parse_qsl,
    urlencode,
    urlparse,
    urlunparse,
)


@dataclass
class NormalizerConfig:
    sort_query_params: bool = True
    remove_fragments: bool = True
    lowercase_host: bool = True
    strip_trailing_slash: bool = True
    remove_default_ports: bool = True
    drop_params: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "NormalizerConfig":
        return cls(
            sort_query_params=data.get("sort_query_params", True),
            remove_fragments=data.get("remove_fragments", True),
            lowercase_host=data.get("lowercase_host", True),
            strip_trailing_slash=data.get("strip_trailing_slash", True),
            remove_default_ports=data.get("remove_default_ports", True),
            drop_params=data.get("drop_params", []),
        )


_DEFAULT_PORTS = {"http": 80, "https": 443, "ftp": 21}


class URLNormalizer:
    def __init__(self, config: Optional[NormalizerConfig] = None) -> None:
        self.config = config or NormalizerConfig()

    def normalize(self, url: str) -> str:
        parsed: ParseResult = urlparse(url)

        scheme = parsed.scheme.lower()
        host = parsed.hostname or ""
        if self.config.lowercase_host:
            host = host.lower()

        port = parsed.port
        if self.config.remove_default_ports and port == _DEFAULT_PORTS.get(scheme):
            port = None
        netloc = host if port is None else f"{host}:{port}"

        path = parsed.path
        if self.config.strip_trailing_slash and path.endswith("/") and len(path) > 1:
            path = path.rstrip("/")

        query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
        if self.config.drop_params:
            drop = set(self.config.drop_params)
            query_pairs = [(k, v) for k, v in query_pairs if k not in drop]
        if self.config.sort_query_params:
            query_pairs = sorted(query_pairs)
        query = urlencode(query_pairs)

        fragment = "" if self.config.remove_fragments else parsed.fragment

        return urlunparse((scheme, netloc, path, parsed.params, query, fragment))

    def are_equivalent(self, url_a: str, url_b: str) -> bool:
        return self.normalize(url_a) == self.normalize(url_b)
