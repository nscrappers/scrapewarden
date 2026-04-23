"""Middleware that integrates RequestLogger with the scrapewarden pipeline."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from scrapewarden.request_logger import RequestLogConfig, RequestLogger, RequestLogEntry
from scrapewarden.stats_collector import StatsCollector
from scrapewarden.domain_utils import extract_domain


class LogMiddleware:
    """Wraps an async callable (e.g. httpx.AsyncClient.request) to log every
    request/response pair and forward stats to a StatsCollector."""

    def __init__(
        self,
        config: Optional[RequestLogConfig] = None,
        stats: Optional[StatsCollector] = None,
    ) -> None:
        self.logger = RequestLogger(config or RequestLogConfig())
        self.stats = stats
        self._entries: list[RequestLogEntry] = []

    @classmethod
    def from_dict(cls, data: Dict[str, Any],
                  stats: Optional[StatsCollector] = None) -> "LogMiddleware":
        return cls(config=RequestLogConfig.from_dict(data), stats=stats)

    @property
    def entries(self) -> list[RequestLogEntry]:
        """All recorded log entries (requests + errors)."""
        return list(self._entries)

    def last_entry(self) -> Optional[RequestLogEntry]:
        return self._entries[-1] if self._entries else None

    async def execute(
        self,
        send_fn: Callable[..., Any],
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        proxy: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Call *send_fn* and log the outcome.  Returns the response object."""
        domain = extract_domain(url)
        start = self.logger.log_request(method, url, headers=headers, proxy=proxy)
        try:
            response = await send_fn(method, url, headers=headers, **kwargs)
            status = getattr(response, "status_code", 0)
            resp_headers = dict(getattr(response, "headers", {}))
            body: Optional[bytes] = None
            if self.logger.config.log_body_preview:
                body = getattr(response, "content", None)
            entry = self.logger.log_response(
                method, url, status, start,
                headers=resp_headers, body=body, proxy=proxy,
            )
            self._entries.append(entry)
            if self.stats and domain:
                success = 200 <= status < 400
                wait = (entry.elapsed_ms or 0) / 1000
                self.stats.record(domain, success=success, wait_seconds=wait)
            return response
        except Exception as exc:
            entry = self.logger.log_error(method, url, str(exc), start, proxy=proxy)
            self._entries.append(entry)
            if self.stats and domain:
                self.stats.record(domain, success=False, wait_seconds=0)
            raise

    def clear(self) -> None:
        """Reset the in-memory entry list."""
        self._entries.clear()
