"""User-agent middleware that integrates UserAgentPool with the request pipeline."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .user_agent_pool import UserAgentPool, UserAgentPoolConfig


class UAMiddleware:
    """Middleware that automatically rotates user-agents per domain.

    Wraps :class:`UserAgentPool` and provides a thin integration layer
    compatible with the rest of the ScrapeWarden middleware family.

    Usage::

        mw = UAMiddleware.from_dict({"rotate_per_domain": True})
        headers = mw.on_request("https://example.com/page")
        # headers contains {"User-Agent": "<selected agent>"}

        # After receiving a response:
        mw.on_response("https://example.com/page", status_code=200)
        mw.on_response("https://example.com/page", status_code=403)
    """

    def __init__(self, pool: UserAgentPool) -> None:
        self._pool = pool
        # Track which agent was last assigned per domain so we can score it.
        self._last_agent: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]] = None) -> "UAMiddleware":
        """Create a :class:`UAMiddleware` from a plain configuration dict.

        Args:
            data: Optional mapping accepted by :meth:`UserAgentPoolConfig.from_dict`.
                  Passing ``None`` or an empty dict uses all defaults.

        Returns:
            A fully initialised :class:`UAMiddleware` instance.
        """
        config = UserAgentPoolConfig.from_dict(data or {})
        pool = UserAgentPool(config)
        return cls(pool)

    # ------------------------------------------------------------------
    # Middleware interface
    # ------------------------------------------------------------------

    def on_request(self, url: str) -> Dict[str, str]:
        """Select a user-agent for *url* and return it as a header dict.

        The chosen agent is remembered so that :meth:`on_response` can
        update its success/failure counters correctly.

        Args:
            url: The full URL of the outgoing request.

        Returns:
            A ``{"User-Agent": "<value>"}`` dict ready to be merged into
            the request headers.  Returns an empty dict when the pool has
            no agents configured.
        """
        agent = self._pool.get(url)
        if agent is None:
            return {}
        self._last_agent[url] = agent
        return {"User-Agent": agent}

    def on_response(self, url: str, status_code: int) -> None:
        """Record the outcome of a request so the pool can adapt.

        Args:
            url:         The URL that was requested.
            status_code: The HTTP status code received.
        """
        agent = self._last_agent.pop(url, None)
        if agent is None:
            return

        # Treat 2xx and 3xx as success; everything else as a failure.
        if 200 <= status_code < 400:
            self._pool.mark_success(agent, url)
        else:
            self._pool.mark_failure(agent, url)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def pool(self) -> UserAgentPool:
        """Expose the underlying :class:`UserAgentPool` for inspection."""
        return self._pool

    def stats(self) -> Dict[str, Any]:
        """Return a snapshot of pool-level statistics.

        Returns:
            A dict with ``total_agents`` and ``pending_responses`` keys,
            plus any extra data exposed by the pool itself.
        """
        return {
            "total_agents": len(self._pool),
            "pending_responses": len(self._last_agent),
        }
