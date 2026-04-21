"""
scrapewarden — Rate-limiting and proxy rotation middleware for Python scraping frameworks.

Provides:
    - TokenBucket-based rate limiting
    - Proxy rotation with ban detection
    - Configurable retry policies
    - Circuit breaker for failing hosts
    - Request deduplication via fingerprinting
    - Unified middleware interface for Scrapy and httpx

Quick start::

    from scrapewarden import ScrapeWardenMiddleware, ScrapeWardenConfig

    config = ScrapeWardenConfig.from_dict({
        "rate_limit": {"rate": 2.0, "burst": 5},
        "proxies": ["http://proxy1:8080", "http://proxy2:8080"],
        "retry": {"max_retries": 3, "retryable_status_codes": [429, 503]},
        "circuit_breaker": {"failure_threshold": 5, "recovery_timeout": 30},
    })

    middleware = ScrapeWardenMiddleware.from_config(config)
"""

from scrapewarden.config import ScrapeWardenConfig
from scrapewarden.middleware import ScrapeWardenMiddleware
from scrapewarden.rate_limiter import RateLimiterConfig, TokenBucket
from scrapewarden.proxy_rotator import ProxyEntry, ProxyRotator
from scrapewarden.retry_policy import RetryPolicy, RetryPolicyConfig, RetryState
from scrapewarden.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
from scrapewarden.request_fingerprinter import FingerprintConfig, RequestFingerprinter

__all__ = [
    # Top-level API
    "ScrapeWardenConfig",
    "ScrapeWardenMiddleware",
    # Rate limiting
    "RateLimiterConfig",
    "TokenBucket",
    # Proxy rotation
    "ProxyEntry",
    "ProxyRotator",
    # Retry policy
    "RetryPolicy",
    "RetryPolicyConfig",
    "RetryState",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    # Request fingerprinting
    "FingerprintConfig",
    "RequestFingerprinter",
]

__version__ = "0.1.0"
__author__ = "scrapewarden contributors"
