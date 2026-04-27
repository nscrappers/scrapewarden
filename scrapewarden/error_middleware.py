"""Middleware that classifies exceptions and records per-domain error stats."""
from __future__ import annotations

from typing import Dict, Optional

from scrapewarden.domain_utils import extract_domain
from scrapewarden.error_classifier import ErrorClass, ErrorClassifier, ErrorClassifierConfig
from scrapewarden.error_stats import ErrorStats


class ErrorMiddleware:
    """Wraps scraping calls, classifies any raised exceptions, and tracks stats."""

    def __init__(self, classifier: Optional[ErrorClassifier] = None) -> None:
        self._classifier = classifier or ErrorClassifier()
        self._stats = ErrorStats()

    @classmethod
    def from_dict(cls, data: Dict) -> "ErrorMiddleware":
        config = ErrorClassifierConfig.from_dict(data)
        return cls(classifier=ErrorClassifier(config))

    def on_error(self, url: str, exc: BaseException) -> ErrorClass:
        """Classify *exc* and record it against the domain of *url*."""
        domain = extract_domain(url)
        error_class = self._classifier.classify(exc)
        self._stats.record(domain, error_class)
        return error_class

    @property
    def stats(self) -> ErrorStats:
        return self._stats

    def summary(self) -> Dict:
        return self._stats.to_dict()
