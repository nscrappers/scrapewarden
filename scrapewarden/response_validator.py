from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ValidatorConfig:
    min_body_length: int = 0
    required_patterns: List[str] = field(default_factory=list)
    forbidden_patterns: List[str] = field(default_factory=list)
    allowed_content_types: List[str] = field(default_factory=list)
    require_utf8: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "ValidatorConfig":
        return cls(
            min_body_length=data.get("min_body_length", 0),
            required_patterns=data.get("required_patterns", []),
            forbidden_patterns=data.get("forbidden_patterns", []),
            allowed_content_types=data.get("allowed_content_types", []),
            require_utf8=data.get("require_utf8", False),
        )


@dataclass
class ValidationResult:
    valid: bool
    reason: Optional[str] = None


class ResponseValidator:
    def __init__(self, config: Optional[ValidatorConfig] = None) -> None:
        self._cfg = config or ValidatorConfig()
        self._required = [re.compile(p) for p in self._cfg.required_patterns]
        self._forbidden = [re.compile(p) for p in self._cfg.forbidden_patterns]

    def validate(self, body: str, content_type: str = "") -> ValidationResult:
        if len(body) < self._cfg.min_body_length:
            return ValidationResult(
                False,
                f"body length {len(body)} below minimum {self._cfg.min_body_length}",
            )

        if self._cfg.allowed_content_types:
            ct_base = content_type.split(";")[0].strip().lower()
            if ct_base not in [c.lower() for c in self._cfg.allowed_content_types]:
                return ValidationResult(
                    False, f"content-type '{ct_base}' not in allowed list"
                )

        if self._cfg.require_utf8:
            try:
                body.encode("utf-8").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                return ValidationResult(False, "body is not valid UTF-8")

        for pattern in self._required:
            if not pattern.search(body):
                return ValidationResult(
                    False, f"required pattern '{pattern.pattern}' not found"
                )

        for pattern in self._forbidden:
            if pattern.search(body):
                return ValidationResult(
                    False, f"forbidden pattern '{pattern.pattern}' matched"
                )

        return ValidationResult(True)
