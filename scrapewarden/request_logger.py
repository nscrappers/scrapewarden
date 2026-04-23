"""Request/response logging middleware for scrapewarden."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger("scrapewarden.request_logger")


@dataclass
class RequestLogConfig:
    enabled: bool = True
    log_request_headers: bool = False
    log_response_headers: bool = False
    log_body_preview: bool = False
    body_preview_length: int = 200
    level: str = "INFO"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RequestLogConfig":
        return cls(
            enabled=data.get("enabled", True),
            log_request_headers=data.get("log_request_headers", False),
            log_response_headers=data.get("log_response_headers", False),
            log_body_preview=data.get("log_body_preview", False),
            body_preview_length=data.get("body_preview_length", 200),
            level=data.get("level", "INFO"),
        )


@dataclass
class RequestLogEntry:
    method: str
    url: str
    status_code: Optional[int] = None
    elapsed_ms: Optional[float] = None
    proxy: Optional[str] = None
    error: Optional[str] = None
    request_headers: Dict[str, str] = field(default_factory=dict)
    response_headers: Dict[str, str] = field(default_factory=dict)
    body_preview: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "url": self.url,
            "status_code": self.status_code,
            "elapsed_ms": round(self.elapsed_ms, 2) if self.elapsed_ms is not None else None,
            "proxy": self.proxy,
            "error": self.error,
        }


class RequestLogger:
    def __init__(self, config: Optional[RequestLogConfig] = None) -> None:
        self.config = config or RequestLogConfig()
        self._log_fn = getattr(logger, self.config.level.lower(), logger.info)

    def log_request(self, method: str, url: str, headers: Optional[Dict[str, str]] = None,
                    proxy: Optional[str] = None) -> float:
        """Log an outgoing request and return the start timestamp."""
        if not self.config.enabled:
            return time.monotonic()
        entry = RequestLogEntry(method=method, url=url, proxy=proxy)
        if self.config.log_request_headers and headers:
            entry.request_headers = dict(headers)
        self._log_fn("→ %s %s proxy=%s", method, url, proxy or "none")
        return time.monotonic()

    def log_response(self, method: str, url: str, status_code: int,
                     start_time: float, headers: Optional[Dict[str, str]] = None,
                     body: Optional[bytes] = None, proxy: Optional[str] = None) -> RequestLogEntry:
        """Log a received response and return the log entry."""
        elapsed_ms = (time.monotonic() - start_time) * 1000
        entry = RequestLogEntry(
            method=method, url=url, status_code=status_code,
            elapsed_ms=elapsed_ms, proxy=proxy,
        )
        if self.config.log_response_headers and headers:
            entry.response_headers = dict(headers)
        if self.config.log_body_preview and body:
            entry.body_preview = body[: self.config.body_preview_length].decode("utf-8", errors="replace")
        if self.config.enabled:
            self._log_fn("← %s %s status=%d elapsed=%.1fms", method, url, status_code, elapsed_ms)
        return entry

    def log_error(self, method: str, url: str, error: str,
                  start_time: float, proxy: Optional[str] = None) -> RequestLogEntry:
        """Log a request error."""
        elapsed_ms = (time.monotonic() - start_time) * 1000
        entry = RequestLogEntry(method=method, url=url, elapsed_ms=elapsed_ms,
                                error=error, proxy=proxy)
        if self.config.enabled:
            logger.error("✗ %s %s error=%s elapsed=%.1fms", method, url, error, elapsed_ms)
        return entry
