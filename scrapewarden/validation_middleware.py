from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .response_validator import ResponseValidator, ValidatorConfig, ValidationResult


class ValidationMiddleware:
    """Middleware that validates response bodies using ResponseValidator."""

    def __init__(self, validator: Optional[ResponseValidator] = None) -> None:
        self._validator = validator or ResponseValidator()
        self._invalid: List[Dict] = []
        self._valid_count: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "ValidationMiddleware":
        cfg = ValidatorConfig.from_dict(data)
        return cls(ResponseValidator(cfg))

    def on_response(
        self,
        url: str,
        body: str,
        content_type: str = "",
        on_invalid: Optional[Callable[[str, ValidationResult], None]] = None,
    ) -> ValidationResult:
        result = self._validator.validate(body, content_type)
        if result.valid:
            self._valid_count += 1
        else:
            self._invalid.append({"url": url, "reason": result.reason})
            if on_invalid:
                on_invalid(url, result)
        return result

    @property
    def invalid_responses(self) -> List[Dict]:
        return list(self._invalid)

    @property
    def valid_count(self) -> int:
        return self._valid_count

    @property
    def invalid_count(self) -> int:
        return len(self._invalid)

    def reset(self) -> None:
        self._invalid.clear()
        self._valid_count = 0

    def stats(self) -> Dict:
        total = self._valid_count + len(self._invalid)
        return {
            "total": total,
            "valid": self._valid_count,
            "invalid": len(self._invalid),
            "invalid_rate": len(self._invalid) / total if total else 0.0,
        }
