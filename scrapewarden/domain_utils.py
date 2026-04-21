"""Utility helpers for extracting and normalising domain names from URLs."""

from urllib.parse import urlparse
from typing import Optional


def extract_domain(url: str, include_port: bool = False) -> Optional[str]:
    """Extract the hostname (and optionally port) from a URL.

    Returns None if the URL cannot be parsed or has no hostname.

    >>> extract_domain("https://www.Example.COM/path?q=1")
    'www.example.com'
    >>> extract_domain("https://api.example.com:8080/v1", include_port=True)
    'api.example.com:8080'
    """
    try:
        parsed = urlparse(url)
        host = parsed.hostname  # already lowercased by urlparse
        if not host:
            return None
        if include_port and parsed.port:
            return f"{host}:{parsed.port}"
        return host
    except Exception:
        return None


def root_domain(domain: str) -> str:
    """Return the registrable root domain (last two labels).

    >>> root_domain("sub.api.example.co.uk")
    'example.co.uk'
    >>> root_domain("example.com")
    'example.com'
    """
    parts = domain.split(".")
    # Naïve two-label heuristic; sufficient for common TLDs
    if len(parts) <= 2:
        return domain
    # Handle common two-part TLDs (co.uk, com.au, …)
    known_second_level = {"co", "com", "net", "org", "gov", "edu", "ac"}
    if len(parts) >= 3 and parts[-2] in known_second_level:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def same_domain(url_a: str, url_b: str) -> bool:
    """Return True if both URLs belong to the same hostname."""
    return extract_domain(url_a) == extract_domain(url_b)


def domain_from_proxy(proxy_url: str) -> Optional[str]:
    """Extract host from a proxy URL (e.g. http://user:pass@proxy.host:8080)."""
    return extract_domain(proxy_url, include_port=False)
