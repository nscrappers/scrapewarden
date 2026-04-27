"""Content-type filtering for responses — skip or flag unwanted MIME types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class ContentTypeConfig:
    allowed_types: List[str] = field(default_factory=lambda: [
        "text/html",
        "application/json",
        "application/xml",
        "text/xml",
        "text/plain",
    ])
    blocked_types: List[str] = field(default_factory=lambda: [
        "application/octet-stream",
        "application/zip",
        "image/png",
        "image/jpeg",
        "image/gif",
        "video/mp4",
        "audio/mpeg",
    ])
    strict: bool = False  # if True, reject anything not in allowed_types

    @classmethod
    def from_dict(cls, data: Dict) -> "ContentTypeConfig":
        cfg = cls()
        if "allowed_types" in data:
            cfg.allowed_types = list(data["allowed_types"])
        if "blocked_types" in data:
            cfg.blocked_types = list(data["blocked_types"])
        if "strict" in data:
            cfg.strict = bool(data["strict"])
        return cfg


class ContentTypeFilter:
    """Determines whether a response content-type should be accepted."""

    def __init__(self, config: Optional[ContentTypeConfig] = None) -> None:
        self._config = config or ContentTypeConfig()
        self._allowed: Set[str] = {self._normalise(t) for t in self._config.allowed_types}
        self._blocked: Set[str] = {self._normalise(t) for t in self._config.blocked_types}

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def is_allowed(self, content_type: str) -> bool:
        """Return True if *content_type* should be processed."""
        base = self._normalise(content_type)
        if base in self._blocked:
            return False
        if self._config.strict and base not in self._allowed:
            return False
        return True

    def is_blocked(self, content_type: str) -> bool:
        return not self.is_allowed(content_type)

    def classify(self, content_type: str) -> str:
        """Return 'allowed', 'blocked', or 'unknown'."""
        base = self._normalise(content_type)
        if base in self._blocked:
            return "blocked"
        if base in self._allowed:
            return "allowed"
        return "blocked" if self._config.strict else "unknown"

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise(content_type: str) -> str:
        """Strip parameters (e.g. '; charset=utf-8') and lower-case."""
        return content_type.split(";")[0].strip().lower()
