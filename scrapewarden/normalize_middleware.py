"""Middleware that normalizes request URLs before they are dispatched."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from .url_normalizer import NormalizerConfig, URLNormalizer


class NormalizeMiddleware:
    """Rewrites request URLs to their canonical form.

    Intended to be inserted early in a middleware chain so that downstream
    components (deduplicator, cache, fingerprinter) all operate on consistent
    URLs.
    """

    def __init__(self, normalizer: Optional[URLNormalizer] = None) -> None:
        self._normalizer = normalizer or URLNormalizer()
        self._rewrite_count: int = 0
        self._history: List[Dict[str, str]] = []

    @classmethod
    def from_dict(cls, data: dict) -> "NormalizeMiddleware":
        config = NormalizerConfig.from_dict(data)
        return cls(normalizer=URLNormalizer(config))

    # ------------------------------------------------------------------
    # Core hook
    # ------------------------------------------------------------------

    def on_request(self, request: dict) -> dict:
        """Normalize the ``url`` key of *request* in-place and return it.

        *request* is expected to be a plain dict with at least a ``"url"`` key,
        matching the lightweight request model used throughout scrapewarden.
        """
        original = request.get("url", "")
        normalized = self._normalizer.normalize(original)
        if normalized != original:
            request["url"] = normalized
            self._rewrite_count += 1
            self._history.append({"original": original, "normalized": normalized})
        return request

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    @property
    def rewrite_count(self) -> int:
        """Total number of URLs that were rewritten."""
        return self._rewrite_count

    @property
    def history(self) -> List[Dict[str, str]]:
        """Read-only view of rewrite history."""
        return list(self._history)

    def reset(self) -> None:
        """Clear counters and history (useful between test runs)."""
        self._rewrite_count = 0
        self._history.clear()
