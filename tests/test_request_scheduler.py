"""Tests for RequestScheduler and SchedulerMiddleware."""
from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from scrapewarden.request_scheduler import RequestScheduler, SchedulerConfig
from scrapewarden.scheduler_middleware import SchedulerMiddleware


# ---------------------------------------------------------------------------
# SchedulerConfig
# ---------------------------------------------------------------------------

class TestSchedulerConfig:
    def test_defaults(self):
        cfg = SchedulerConfig()
        assert cfg.max_queue_size == 1000
        assert cfg.default_priority == 5
        assert cfg.domain_cooldown == 0.5

    def test_from_dict(self):
        cfg = SchedulerConfig.from_dict({"max_queue_size": 50, "domain_cooldown": 1.0})
        assert cfg.max_queue_size == 50
        assert cfg.domain_cooldown == 1.0

    def test_from_dict_defaults(self):
        cfg = SchedulerConfig.from_dict({})
        assert cfg.default_priority == 5


# ---------------------------------------------------------------------------
# RequestScheduler
# ---------------------------------------------------------------------------

@pytest.fixture
def scheduler():
    return RequestScheduler(SchedulerConfig(domain_cooldown=0.0))


class TestRequestScheduler:
    def test_submit_and_pop(self, scheduler):
        scheduler.submit("req-a", domain="example.com")
        result = scheduler.next_request()
        assert result == "req-a"

    def test_priority_ordering(self, scheduler):
        scheduler.submit("low", domain="a.com", priority=9)
        scheduler.submit("high", domain="b.com", priority=1)
        assert scheduler.next_request() == "high"
        assert scheduler.next_request() == "low"

    def test_returns_none_when_empty(self, scheduler):
        assert scheduler.next_request() is None

    def test_queue_full_returns_false(self):
        cfg = SchedulerConfig(max_queue_size=2, domain_cooldown=0.0)
        s = RequestScheduler(cfg)
        assert s.submit("r1", "x.com") is True
        assert s.submit("r2", "x.com") is True
        assert s.submit("r3", "x.com") is False

    def test_domain_cooldown_respected(self):
        cfg = SchedulerConfig(domain_cooldown=10.0)  # very long cooldown
        s = RequestScheduler(cfg)
        s.submit("r1", "example.com")
        s.submit("r2", "example.com")
        # First pop should succeed
        assert s.next_request() == "r1"
        # Second pop should return None (cooldown not elapsed)
        assert s.next_request() is None

    def test_size_reflects_queue(self, scheduler):
        assert scheduler.size == 0
        scheduler.submit("r", "a.com")
        assert scheduler.size == 1
        scheduler.next_request()
        assert scheduler.size == 0

    def test_from_dict(self):
        s = RequestScheduler.from_dict({"max_queue_size": 10, "domain_cooldown": 0.0})
        assert s.config.max_queue_size == 10


# ---------------------------------------------------------------------------
# SchedulerMiddleware
# ---------------------------------------------------------------------------

@pytest.fixture
def mw():
    return SchedulerMiddleware.from_dict({"domain_cooldown": 0.0})


class TestSchedulerMiddleware:
    def _req(self, url: str):
        return SimpleNamespace(url=url)

    def test_on_request_enqueues(self, mw):
        accepted = mw.on_request(self._req("https://example.com/page"))
        assert accepted is True
        assert mw.queue_size == 1
        assert mw.submitted == 1

    def test_dropped_when_full(self):
        m = SchedulerMiddleware.from_dict({"max_queue_size": 1, "domain_cooldown": 0.0})
        m.on_request(SimpleNamespace(url="https://a.com"))
        dropped = m.on_request(SimpleNamespace(url="https://b.com"))
        assert dropped is False
        assert m.dropped == 1

    def test_next_request_returns_request(self, mw):
        req = self._req("https://example.com")
        mw.on_request(req)
        assert mw.next_request() is req

    def test_stats_dict(self, mw):
        mw.on_request(self._req("https://x.com"))
        s = mw.stats()
        assert "queue_size" in s
        assert "submitted" in s
        assert "dropped" in s
