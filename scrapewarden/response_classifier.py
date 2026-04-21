"""Response classifier for determining if a scraping response indicates success, soft block, or hard failure."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ResponseClass(Enum):
    SUCCESS = "success"
    SOFT_BLOCK = "soft_block"   # e.g. CAPTCHA, 429, temporary ban
    HARD_FAILURE = "hard_failure"  # e.g. 404, 403 permanent
    TRANSIENT_ERROR = "transient_error"  # e.g. 500, 503, network error


@dataclass
class ClassifierConfig:
    soft_block_status_codes: List[int] = field(default_factory=lambda: [429, 503])
    hard_failure_status_codes: List[int] = field(default_factory=lambda: [403, 404, 410])
    transient_error_status_codes: List[int] = field(default_factory=lambda: [500, 502, 504])
    captcha_body_patterns: List[str] = field(default_factory=lambda: ["captcha", "robot", "unusual traffic"])

    @classmethod
    def from_dict(cls, data: dict) -> "ClassifierConfig":
        return cls(
            soft_block_status_codes=data.get("soft_block_status_codes", [429, 503]),
            hard_failure_status_codes=data.get("hard_failure_status_codes", [403, 404, 410]),
            transient_error_status_codes=data.get("transient_error_status_codes", [500, 502, 504]),
            captcha_body_patterns=data.get("captcha_body_patterns", ["captcha", "robot", "unusual traffic"]),
        )


class ResponseClassifier:
    def __init__(self, config: Optional[ClassifierConfig] = None):
        self.config = config or ClassifierConfig()

    def classify(self, status_code: int, body: str = "") -> ResponseClass:
        """Classify an HTTP response based on status code and optional body content."""
        if status_code in self.config.soft_block_status_codes:
            return ResponseClass.SOFT_BLOCK

        if status_code in self.config.hard_failure_status_codes:
            return ResponseClass.HARD_FAILURE

        if status_code in self.config.transient_error_status_codes:
            return ResponseClass.TRANSIENT_ERROR

        if 200 <= status_code < 300:
            body_lower = body.lower()
            for pattern in self.config.captcha_body_patterns:
                if pattern.lower() in body_lower:
                    return ResponseClass.SOFT_BLOCK
            return ResponseClass.SUCCESS

        # Catch-all for unexpected codes
        if status_code >= 500:
            return ResponseClass.TRANSIENT_ERROR
        if status_code >= 400:
            return ResponseClass.HARD_FAILURE

        return ResponseClass.SUCCESS

    def is_retryable(self, response_class: ResponseClass) -> bool:
        """Return True if the response class warrants a retry attempt."""
        return response_class in (ResponseClass.SOFT_BLOCK, ResponseClass.TRANSIENT_ERROR)

    def should_rotate_proxy(self, response_class: ResponseClass) -> bool:
        """Return True if the response class suggests the proxy should be rotated."""
        return response_class == ResponseClass.SOFT_BLOCK
