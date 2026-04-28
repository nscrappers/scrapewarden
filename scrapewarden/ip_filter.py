"""IP address filtering and blocklist management for scrapewarden.

Provides allow/deny list filtering for outbound request IPs and
proxy IPs, with support for CIDR ranges and dynamic blocklists.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import List, Optional, Set, Union

# Type alias for IP network objects
_Network = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


@dataclass
class IPFilterConfig:
    """Configuration for IP filtering behaviour."""

    # Explicit IPs or CIDR ranges that are always allowed (empty = allow all)
    allowlist: List[str] = field(default_factory=list)
    # Explicit IPs or CIDR ranges that are always blocked
    blocklist: List[str] = field(default_factory=list)
    # When True, block private/loopback/link-local ranges automatically
    block_private: bool = False
    # When True, block IPv6 addresses entirely
    block_ipv6: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "IPFilterConfig":
        """Construct config from a plain dictionary."""
        return cls(
            allowlist=data.get("allowlist", []),
            blocklist=data.get("blocklist", []),
            block_private=bool(data.get("block_private", False)),
            block_ipv6=bool(data.get("block_ipv6", False)),
        )


def _parse_networks(entries: List[str]) -> List[_Network]:
    """Parse a list of IP/CIDR strings into network objects."""
    networks: List[_Network] = []
    for entry in entries:
        try:
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            # Skip malformed entries rather than crashing
            pass
    return networks


class IPFilter:
    """Filters IP addresses based on allow/deny lists and policy flags."""

    def __init__(self, config: Optional[IPFilterConfig] = None) -> None:
        self._config = config or IPFilterConfig()
        self._allowlist = _parse_networks(self._config.allowlist)
        self._blocklist = _parse_networks(self._config.blocklist)
        # Runtime-added blocked IPs (e.g. from abuse detection)
        self._dynamic_blocked: Set[str] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_allowed(self, ip: str) -> bool:
        """Return True if *ip* is permitted under the current policy."""
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            # Unparseable address is denied by default
            return False

        # Dynamic runtime blocklist takes priority
        if ip in self._dynamic_blocked:
            return False

        # Block IPv6 if configured
        if self._config.block_ipv6 and isinstance(addr, ipaddress.IPv6Address):
            return False

        # Block private/special-use ranges if configured
        if self._config.block_private and self._is_private(addr):
            return False

        # Explicit blocklist check
        if any(addr in net for net in self._blocklist):
            return False

        # Explicit allowlist check (if populated, acts as whitelist)
        if self._allowlist:
            return any(addr in net for net in self._allowlist)

        return True

    def block(self, ip: str) -> None:
        """Dynamically add *ip* to the runtime blocklist."""
        self._dynamic_blocked.add(ip)

    def unblock(self, ip: str) -> None:
        """Remove *ip* from the runtime blocklist."""
        self._dynamic_blocked.discard(ip)

    @property
    def dynamic_blocked(self) -> Set[str]:
        """Return a copy of the current dynamic blocklist."""
        return set(self._dynamic_blocked)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_private(
        addr: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
    ) -> bool:
        """Return True for loopback, private, link-local, and reserved ranges."""
        return (
            addr.is_loopback
            or addr.is_private
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
        )
