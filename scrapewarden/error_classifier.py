"""Classify errors and exceptions encountered during scraping."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Type


class ErrorClass(str, Enum):
    NETWORK = "network"
    TIMEOUT = "timeout"
    DNS = "dns"
    SSL = "ssl"
    HTTP = "http"
    PROXY = "proxy"
    UNKNOWN = "unknown"


@dataclass
class ErrorClassifierConfig:
    network_exceptions: List[str] = field(default_factory=lambda: [
        "ConnectionError", "ConnectionResetError", "BrokenPipeError"
    ])
    timeout_exceptions: List[str] = field(default_factory=lambda: [
        "TimeoutError", "asyncio.TimeoutError", "socket.timeout"
    ])
    dns_exceptions: List[str] = field(default_factory=lambda: [
        "socket.gaierror", "dns.resolver.NXDOMAIN"
    ])
    ssl_exceptions: List[str] = field(default_factory=lambda: [
        "ssl.SSLError", "ssl.CertificateError"
    ])
    proxy_exceptions: List[str] = field(default_factory=lambda: [
        "ProxyError", "ProxyConnectionError"
    ])

    @classmethod
    def from_dict(cls, data: Dict) -> "ErrorClassifierConfig":
        return cls(
            network_exceptions=data.get("network_exceptions", cls.__dataclass_fields__["network_exceptions"].default_factory()),
            timeout_exceptions=data.get("timeout_exceptions", cls.__dataclass_fields__["timeout_exceptions"].default_factory()),
            dns_exceptions=data.get("dns_exceptions", cls.__dataclass_fields__["dns_exceptions"].default_factory()),
            ssl_exceptions=data.get("ssl_exceptions", cls.__dataclass_fields__["ssl_exceptions"].default_factory()),
            proxy_exceptions=data.get("proxy_exceptions", cls.__dataclass_fields__["proxy_exceptions"].default_factory()),
        )


class ErrorClassifier:
    def __init__(self, config: Optional[ErrorClassifierConfig] = None) -> None:
        self._config = config or ErrorClassifierConfig()
        self._map: Dict[str, ErrorClass] = {}
        for name in self._config.network_exceptions:
            self._map[name] = ErrorClass.NETWORK
        for name in self._config.timeout_exceptions:
            self._map[name] = ErrorClass.TIMEOUT
        for name in self._config.dns_exceptions:
            self._map[name] = ErrorClass.DNS
        for name in self._config.ssl_exceptions:
            self._map[name] = ErrorClass.SSL
        for name in self._config.proxy_exceptions:
            self._map[name] = ErrorClass.PROXY

    def classify(self, exc: BaseException) -> ErrorClass:
        type_name = type(exc).__name__
        qualified = f"{type(exc).__module__}.{type_name}"
        return (
            self._map.get(type_name)
            or self._map.get(qualified)
            or ErrorClass.UNKNOWN
        )

    def classify_by_name(self, name: str) -> ErrorClass:
        return self._map.get(name, ErrorClass.UNKNOWN)
