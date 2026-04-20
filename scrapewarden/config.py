"""Configuration loading and validation for ScrapeWarden middleware."""

from __future__ import annotations

import os
from typing import Any
from dataclasses import dataclass, field

from scrapewarden.rate_limiter import RateLimiterConfig

_DEFAULTS = {
    "SCRAPEWARDEN_REQUESTS_PER_SECOND": 1.0,
    "SCRAPEWARDEN_BURST_SIZE": 5,
}


@dataclass
class ScrapeWardenConfig:
    rate_limiter: RateLimiterConfig = field(default_factory=RateLimiterConfig)
    enabled: bool = True
    debug: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScrapeWardenConfig":
        """Build config from a plain dict (e.g. Scrapy settings)."""
        rps = float(data.get("SCRAPEWARDEN_REQUESTS_PER_SECOND", _DEFAULTS["SCRAPEWARDEN_REQUESTS_PER_SECOND"]))
        burst = int(data.get("SCRAPEWARDEN_BURST_SIZE", _DEFAULTS["SCRAPEWARDEN_BURST_SIZE"]))
        overrides = data.get("SCRAPEWARDEN_DOMAIN_OVERRIDES", {})

        if rps <= 0:
            raise ValueError("SCRAPEWARDEN_REQUESTS_PER_SECOND must be > 0")
        if burst < 1:
            raise ValueError("SCRAPEWARDEN_BURST_SIZE must be >= 1")

        return cls(
            rate_limiter=RateLimiterConfig(
                requests_per_second=rps,
                burst_size=burst,
                domain_overrides=overrides,
            ),
            enabled=bool(data.get("SCRAPEWARDEN_ENABLED", True)),
            debug=bool(data.get("SCRAPEWARDEN_DEBUG", False)),
        )

    @classmethod
    def from_env(cls) -> "ScrapeWardenConfig":
        """Build config from environment variables."""
        return cls.from_dict(
            {
                "SCRAPEWARDEN_REQUESTS_PER_SECOND": os.getenv(
                    "SCRAPEWARDEN_REQUESTS_PER_SECOND",
                    str(_DEFAULTS["SCRAPEWARDEN_REQUESTS_PER_SECOND"]),
                ),
                "SCRAPEWARDEN_BURST_SIZE": os.getenv(
                    "SCRAPEWARDEN_BURST_SIZE",
                    str(_DEFAULTS["SCRAPEWARDEN_BURST_SIZE"]),
                ),
                "SCRAPEWARDEN_ENABLED": os.getenv("SCRAPEWARDEN_ENABLED", "true").lower() == "true",
                "SCRAPEWARDEN_DEBUG": os.getenv("SCRAPEWARDEN_DEBUG", "false").lower() == "true",
            }
        )
