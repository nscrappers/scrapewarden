from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from .proxy_rotator import ProxyRotator
from .rate_limiter import RateLimiterConfig, TokenBucket

logger = logging.getLogger(__name__)


@dataclass
class ScrapeWardenMiddleware:
    """Combines rate limiting and proxy rotation into a single middleware."""

    rotator: Optional[ProxyRotator] = None
    rate_limiter: Optional[TokenBucket] = None
    on_proxy_failure: Optional[Callable[[str], None]] = None
    _stats: Dict[str, int] = field(default_factory=lambda: {
        "requests": 0,
        "proxy_failures": 0,
        "rate_limited": 0,
    })

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "ScrapeWardenMiddleware":
        rotator = None
        if proxies := config.get("proxies"):
            rotator = ProxyRotator.from_list(
                proxies,
                strategy=config.get("proxy_strategy", "round_robin"),
                ban_duration=config.get("ban_duration", 60.0),
            )

        rate_limiter = None
        if rl_cfg := config.get("rate_limiter"):
            rl_config = RateLimiterConfig(
                rate=rl_cfg.get("rate", 1.0),
                burst=rl_cfg.get("burst", 1),
            )
            rate_limiter = TokenBucket(config=rl_config)

        return cls(rotator=rotator, rate_limiter=rate_limiter)

    async def acquire(self) -> Optional[str]:
        """Wait for rate limit token and return a proxy URL (or None)."""
        if self.rate_limiter is not None:
            wait = self.rate_limiter.consume()
            if wait > 0:
                self._stats["rate_limited"] += 1
                logger.debug("Rate limited: sleeping %.3fs", wait)
                await asyncio.sleep(wait)

        self._stats["requests"] += 1

        if self.rotator is not None:
            proxy = self.rotator.get_proxy()
            if proxy is None:
                logger.warning("No available proxies.")
                return None
            return proxy.url

        return None

    def report_proxy_result(self, proxy_url: str, success: bool) -> None:
        if self.rotator is None:
            return
        if success:
            self.rotator.report_success(proxy_url)
        else:
            self._stats["proxy_failures"] += 1
            self.rotator.report_failure(proxy_url)
            if self.on_proxy_failure:
                self.on_proxy_failure(proxy_url)

    @property
    def stats(self) -> Dict[str, int]:
        return dict(self._stats)
