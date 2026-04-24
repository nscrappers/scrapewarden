import pytest
from scrapewarden.timeout_manager import TimeoutConfig, TimeoutManager
from scrapewarden.timeout_middleware import TimeoutMiddleware


class TestTimeoutConfig:
    def test_defaults(self):
        cfg = TimeoutConfig()
        assert cfg.default_timeout == 30.0
        assert cfg.connect_timeout == 10.0
        assert cfg.read_timeout == 20.0
        assert cfg.backoff_on_timeout is True
        assert cfg.backoff_multiplier == 1.5
        assert cfg.max_timeout == 120.0

    def test_from_dict(self):
        cfg = TimeoutConfig.from_dict({"default_timeout": 60.0, "max_timeout": 200.0})
        assert cfg.default_timeout == 60.0
        assert cfg.max_timeout == 200.0

    def test_from_dict_defaults(self):
        cfg = TimeoutConfig.from_dict({})
        assert cfg.connect_timeout == 10.0


@pytest.fixture
def manager():
    cfg = TimeoutConfig(default_timeout=30.0, backoff_multiplier=2.0, max_timeout=120.0)
    return TimeoutManager(config=cfg)


class TestTimeoutManager:
    def test_default_timeout_returned(self, manager):
        assert manager.get_timeout("example.com") == 30.0

    def test_per_domain_timeout_override(self):
        cfg = TimeoutConfig(per_domain_timeouts={"slow.com": 60.0})
        mgr = TimeoutManager(config=cfg)
        assert mgr.get_timeout("slow.com") == 60.0
        assert mgr.get_timeout("other.com") == 30.0

    def test_backoff_after_timeout(self, manager):
        manager.record_timeout("example.com")
        assert manager.get_timeout("example.com") == 60.0

    def test_backoff_accumulates(self, manager):
        manager.record_timeout("example.com")
        manager.record_timeout("example.com")
        assert manager.get_timeout("example.com") == 120.0

    def test_backoff_capped_at_max(self, manager):
        for _ in range(10):
            manager.record_timeout("example.com")
        assert manager.get_timeout("example.com") <= 120.0

    def test_success_resets_timeout(self, manager):
        manager.record_timeout("example.com")
        manager.record_success("example.com")
        assert manager.get_timeout("example.com") == 30.0

    def test_timeout_count_increments(self, manager):
        assert manager.timeout_count("example.com") == 0
        manager.record_timeout("example.com")
        manager.record_timeout("example.com")
        assert manager.timeout_count("example.com") == 2

    def test_timeout_count_reset_on_success(self, manager):
        manager.record_timeout("example.com")
        manager.record_success("example.com")
        assert manager.timeout_count("example.com") == 0

    def test_reset_clears_all(self, manager):
        manager.record_timeout("a.com")
        manager.record_timeout("b.com")
        manager.reset()
        assert manager.get_timeout("a.com") == 30.0
        assert manager.timeout_count("b.com") == 0


class TestTimeoutMiddleware:
    def test_get_timeouts_returns_dict(self):
        mw = TimeoutMiddleware.from_dict({})
        result = mw.get_timeouts("https://example.com/page")
        assert "timeout" in result
        assert "connect_timeout" in result

    def test_on_timeout_increases_timeout(self):
        mw = TimeoutMiddleware.from_dict({"default_timeout": 30.0, "backoff_multiplier": 2.0})
        mw.on_timeout("https://slow.com/page")
        assert mw.get_timeouts("https://slow.com/page")["timeout"] == 60.0

    def test_on_success_resets(self):
        mw = TimeoutMiddleware.from_dict({"default_timeout": 30.0})
        mw.on_timeout("https://example.com/")
        mw.on_success("https://example.com/")
        assert mw.get_timeouts("https://example.com/")["timeout"] == 30.0

    def test_timeout_count(self):
        mw = TimeoutMiddleware()
        mw.on_timeout("https://example.com/")
        assert mw.timeout_count("https://example.com/") == 1

    def test_reset(self):
        mw = TimeoutMiddleware()
        mw.on_timeout("https://example.com/")
        mw.reset()
        assert mw.timeout_count("https://example.com/") == 0
