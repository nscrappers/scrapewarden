"""Tests for scrapewarden.session_tracker."""

import pytest
from scrapewarden.session_tracker import SessionConfig, DomainSession, SessionTracker


class TestSessionConfig:
    def test_defaults(self):
        cfg = SessionConfig()
        assert cfg.window_seconds == 60.0
        assert cfg.max_history == 200

    def test_from_dict(self):
        cfg = SessionConfig.from_dict({"window_seconds": "30", "max_history": "50"})
        assert cfg.window_seconds == 30.0
        assert cfg.max_history == 50

    def test_from_dict_defaults(self):
        cfg = SessionConfig.from_dict({})
        assert cfg.window_seconds == 60.0


class TestDomainSession:
    @pytest.fixture
    def session(self):
        return DomainSession(domain="example.com", config=SessionConfig(window_seconds=10.0))

    def test_initial_state(self, session):
        assert session.total_requests == 0
        assert session.failure_rate == 0.0
        assert session.last_seen is None

    def test_record_success(self, session):
        session.record_request(success=True, ts=100.0)
        assert session.total_requests == 1
        assert session.failure_rate == 0.0
        assert session.last_seen == 100.0

    def test_record_failure(self, session):
        session.record_request(success=False, ts=100.0)
        assert session.total_requests == 1
        assert session.failure_rate == 1.0

    def test_mixed_failure_rate(self, session):
        session.record_request(success=True, ts=100.0)
        session.record_request(success=True, ts=101.0)
        session.record_request(success=False, ts=102.0)
        assert session.failure_rate == pytest.approx(1 / 3)

    def test_recent_request_count_within_window(self, session):
        session.record_request(success=True, ts=100.0)
        session.record_request(success=True, ts=105.0)
        assert session.recent_request_count(ts=108.0) == 2

    def test_recent_request_count_excludes_old(self, session):
        session.record_request(success=True, ts=90.0)
        session.record_request(success=True, ts=105.0)
        assert session.recent_request_count(ts=108.0) == 1

    def test_max_history_respected(self):
        cfg = SessionConfig(window_seconds=1000.0, max_history=3)
        s = DomainSession(domain="x.com", config=cfg)
        for i in range(5):
            s.record_request(success=True, ts=float(i))
        assert len(s._timestamps) == 3


class TestSessionTracker:
    @pytest.fixture
    def tracker(self):
        return SessionTracker(SessionConfig(window_seconds=10.0))

    def test_record_and_recent_count(self, tracker):
        tracker.record("a.com", success=True, ts=100.0)
        tracker.record("a.com", success=True, ts=105.0)
        assert tracker.recent_count("a.com", ts=108.0) == 2

    def test_unknown_domain_returns_zero(self, tracker):
        assert tracker.recent_count("unknown.com") == 0
        assert tracker.failure_rate("unknown.com") == 0.0

    def test_failure_rate(self, tracker):
        tracker.record("b.com", success=True, ts=1.0)
        tracker.record("b.com", success=False, ts=2.0)
        assert tracker.failure_rate("b.com") == pytest.approx(0.5)

    def test_known_domains(self, tracker):
        tracker.record("c.com", success=True, ts=1.0)
        tracker.record("d.com", success=False, ts=2.0)
        assert set(tracker.known_domains()) == {"c.com", "d.com"}

    def test_reset_removes_domain(self, tracker):
        tracker.record("e.com", success=True, ts=1.0)
        tracker.reset("e.com")
        assert "e.com" not in tracker.known_domains()
        assert tracker.recent_count("e.com") == 0

    def test_get_or_create_idempotent(self, tracker):
        s1 = tracker.get_or_create("f.com")
        s2 = tracker.get_or_create("f.com")
        assert s1 is s2
