"""Tests for scrapewarden.request_queue."""
import time

import pytest

from scrapewarden.request_queue import QueueConfig, RequestQueue


# ---------------------------------------------------------------------------
# QueueConfig
# ---------------------------------------------------------------------------

class TestQueueConfig:
    def test_defaults(self):
        cfg = QueueConfig()
        assert cfg.max_size == 1000
        assert cfg.default_priority == 5
        assert cfg.domain_slot_interval == 0.5

    def test_from_dict(self):
        cfg = QueueConfig.from_dict({"max_size": 50, "default_priority": 2, "domain_slot_interval": 1.0})
        assert cfg.max_size == 50
        assert cfg.default_priority == 2
        assert cfg.domain_slot_interval == 1.0

    def test_from_dict_defaults(self):
        cfg = QueueConfig.from_dict({})
        assert cfg.max_size == 1000


# ---------------------------------------------------------------------------
# RequestQueue
# ---------------------------------------------------------------------------

@pytest.fixture
def queue():
    cfg = QueueConfig(max_size=10, default_priority=5, domain_slot_interval=0.0)
    return RequestQueue(cfg)


class TestRequestQueue:
    def test_enqueue_and_size(self, queue):
        assert queue.enqueue("req1", domain="a.com")
        assert queue.size == 1

    def test_dequeue_returns_request(self, queue):
        queue.enqueue("req1", domain="a.com")
        r = queue.dequeue()
        assert r == "req1"
        assert queue.size == 0

    def test_priority_ordering(self, queue):
        queue.enqueue("low", domain="a.com", priority=9)
        queue.enqueue("high", domain="b.com", priority=1)
        assert queue.dequeue() == "high"
        assert queue.dequeue() == "low"

    def test_full_queue_rejects(self):
        cfg = QueueConfig(max_size=2, domain_slot_interval=0.0)
        q = RequestQueue(cfg)
        assert q.enqueue("r1", domain="x.com")
        assert q.enqueue("r2", domain="y.com")
        assert not q.enqueue("r3", domain="z.com")

    def test_dequeue_empty_returns_none(self, queue):
        assert queue.dequeue() is None

    def test_clear_resets_state(self, queue):
        queue.enqueue("r", domain="a.com")
        queue.clear()
        assert queue.size == 0
        assert queue.dequeue() is None

    def test_domain_slot_interval_delays(self):
        cfg = QueueConfig(max_size=10, domain_slot_interval=0.3)
        q = RequestQueue(cfg)
        q.enqueue("r1", domain="same.com")
        q.enqueue("r2", domain="same.com")
        first = q.dequeue()
        assert first == "r1"
        # second request for same domain should be withheld immediately
        assert q.dequeue() is None
        time.sleep(0.35)
        assert q.dequeue() == "r2"

    def test_is_full_property(self):
        cfg = QueueConfig(max_size=1, domain_slot_interval=0.0)
        q = RequestQueue(cfg)
        assert not q.is_full()
        q.enqueue("r", domain="a.com")
        assert q.is_full()
