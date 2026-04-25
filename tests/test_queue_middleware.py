"""Tests for scrapewarden.queue_middleware."""
import pytest

from scrapewarden.queue_middleware import QueueMiddleware


@pytest.fixture
def mw():
    return QueueMiddleware.from_dict({"max_size": 20, "domain_slot_interval": 0.0})


class TestQueueMiddlewareInit:
    def test_from_dict_creates_instance(self, mw):
        assert isinstance(mw, QueueMiddleware)

    def test_default_from_dict(self):
        m = QueueMiddleware.from_dict({})
        assert m.config.max_size == 1000

    def test_initial_size_zero(self, mw):
        assert mw.size == 0


class TestQueueMiddlewareBehavior:
    def test_submit_and_next(self, mw):
        mw.submit("req", domain="a.com")
        assert mw.next_request() == "req"

    def test_next_on_empty_returns_none(self, mw):
        assert mw.next_request() is None

    def test_is_full_after_max(self):
        m = QueueMiddleware.from_dict({"max_size": 2, "domain_slot_interval": 0.0})
        m.submit("r1", domain="a.com")
        m.submit("r2", domain="b.com")
        assert m.is_full
        assert not m.submit("r3", domain="c.com")

    def test_drain_calls_handler(self, mw):
        mw.submit("r1", domain="a.com")
        mw.submit("r2", domain="b.com")
        collected = []
        count = mw.drain(collected.append)
        assert count == 2
        assert set(collected) == {"r1", "r2"}

    def test_reset_clears_queue(self, mw):
        mw.submit("r", domain="a.com")
        mw.reset()
        assert mw.size == 0
        assert mw.next_request() is None

    def test_priority_respected(self, mw):
        mw.submit("low", domain="a.com", priority=9)
        mw.submit("high", domain="b.com", priority=1)
        assert mw.next_request() == "high"
