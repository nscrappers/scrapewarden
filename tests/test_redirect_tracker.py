import pytest
from scrapewarden.redirect_tracker import (
    RedirectConfig,
    RedirectChain,
    RedirectTracker,
    TooManyRedirectsError,
    CrossDomainRedirectError,
)


class TestRedirectConfig:
    def test_defaults(self):
        cfg = RedirectConfig()
        assert cfg.max_redirects == 10
        assert cfg.track_history is True
        assert cfg.allow_cross_domain is True
        assert "file" in cfg.blocked_schemes

    def test_from_dict(self):
        cfg = RedirectConfig.from_dict({"max_redirects": 5, "allow_cross_domain": False})
        assert cfg.max_redirects == 5
        assert cfg.allow_cross_domain is False

    def test_from_dict_defaults(self):
        cfg = RedirectConfig.from_dict({})
        assert cfg.max_redirects == 10


class TestRedirectChain:
    def test_initial_empty(self):
        chain = RedirectChain()
        assert chain.count == 0
        assert chain.origin is None
        assert chain.final is None

    def test_add_single(self):
        chain = RedirectChain()
        chain.add("http://example.com")
        assert chain.origin == "http://example.com"
        assert chain.final == "http://example.com"
        assert chain.count == 0

    def test_count_reflects_redirects(self):
        chain = RedirectChain()
        chain.add("http://a.com")
        chain.add("http://b.com")
        chain.add("http://c.com")
        assert chain.count == 2

    def test_crossed_domain_false_same(self):
        chain = RedirectChain()
        chain.add("http://example.com/a")
        chain.add("http://example.com/b")
        assert chain.crossed_domain() is False

    def test_crossed_domain_true(self):
        chain = RedirectChain()
        chain.add("http://example.com")
        chain.add("http://other.com")
        assert chain.crossed_domain() is True


class TestRedirectTracker:
    @pytest.fixture
    def tracker(self):
        return RedirectTracker(RedirectConfig(max_redirects=3))

    def test_start_creates_chain(self, tracker):
        chain = tracker.start("req1", "http://example.com")
        assert chain.origin == "http://example.com"

    def test_record_appends_url(self, tracker):
        tracker.start("req1", "http://example.com")
        tracker.record("req1", "http://example.com/page")
        chain = tracker.get("req1")
        assert chain.count == 1
        assert chain.final == "http://example.com/page"

    def test_exceeds_max_redirects_raises(self, tracker):
        tracker.start("req1", "http://a.com")
        tracker.record("req1", "http://b.com")
        tracker.record("req1", "http://c.com")
        tracker.record("req1", "http://d.com")
        with pytest.raises(TooManyRedirectsError):
            tracker.record("req1", "http://e.com")

    def test_blocked_scheme_raises(self, tracker):
        tracker.start("req1", "http://example.com")
        with pytest.raises(ValueError, match="Blocked redirect scheme"):
            tracker.record("req1", "file:///etc/passwd")

    def test_cross_domain_blocked_when_disabled(self):
        cfg = RedirectConfig(allow_cross_domain=False)
        tracker = RedirectTracker(cfg)
        tracker.start("req1", "http://example.com")
        with pytest.raises(CrossDomainRedirectError):
            tracker.record("req1", "http://other.com")

    def test_cross_domain_allowed_by_default(self, tracker):
        tracker.start("req1", "http://example.com")
        tracker.record("req1", "http://other.com")  # should not raise
        chain = tracker.get("req1")
        assert chain.crossed_domain() is True

    def test_clear_removes_chain(self, tracker):
        tracker.start("req1", "http://example.com")
        tracker.clear("req1")
        assert tracker.get("req1") is None

    def test_record_without_start_auto_creates(self, tracker):
        tracker.record("req2", "http://example.com")
        chain = tracker.get("req2")
        assert chain is not None
        assert chain.origin == "http://example.com"
