"""Tests for DomainCookieJar and CookieJarConfig."""

import time
import pytest
from http.cookiejar import CookieJar

from scrapewarden.cookie_jar import CookieJarConfig, DomainCookieJar


class TestCookieJarConfig:
    def test_defaults(self):
        cfg = CookieJarConfig()
        assert cfg.enabled is True
        assert cfg.max_cookies_per_domain == 50
        assert cfg.ttl_seconds == 3600.0
        assert cfg.isolate_by_domain is True

    def test_from_dict(self):
        cfg = CookieJarConfig.from_dict(
            {"enabled": False, "max_cookies_per_domain": 10, "ttl_seconds": None}
        )
        assert cfg.enabled is False
        assert cfg.max_cookies_per_domain == 10
        assert cfg.ttl_seconds is None

    def test_from_dict_defaults(self):
        cfg = CookieJarConfig.from_dict({})
        assert cfg.enabled is True
        assert cfg.ttl_seconds == 3600.0


class TestDomainCookieJar:
    @pytest.fixture
    def jar_manager(self):
        return DomainCookieJar(CookieJarConfig())

    def test_returns_cookie_jar_instance(self, jar_manager):
        jar = jar_manager.get_jar("example.com")
        assert isinstance(jar, CookieJar)

    def test_same_domain_returns_same_jar(self, jar_manager):
        jar1 = jar_manager.get_jar("example.com")
        jar2 = jar_manager.get_jar("example.com")
        assert jar1 is jar2

    def test_different_domains_return_different_jars(self, jar_manager):
        jar1 = jar_manager.get_jar("example.com")
        jar2 = jar_manager.get_jar("other.com")
        assert jar1 is not jar2

    def test_disabled_returns_none(self):
        mgr = DomainCookieJar(CookieJarConfig(enabled=False))
        assert mgr.get_jar("example.com") is None

    def test_clear_removes_domain(self, jar_manager):
        jar_manager.get_jar("example.com")
        assert jar_manager.domain_count() == 1
        jar_manager.clear("example.com")
        assert jar_manager.domain_count() == 0

    def test_clear_all(self, jar_manager):
        jar_manager.get_jar("a.com")
        jar_manager.get_jar("b.com")
        jar_manager.clear_all()
        assert jar_manager.domain_count() == 0

    def test_record_and_read_cookie_count(self, jar_manager):
        jar_manager.get_jar("example.com")
        jar_manager.record_cookies("example.com", 5)
        assert jar_manager.cookie_count("example.com") == 5

    def test_cookie_count_capped_at_max(self):
        mgr = DomainCookieJar(CookieJarConfig(max_cookies_per_domain=10))
        mgr.get_jar("example.com")
        mgr.record_cookies("example.com", 999)
        assert mgr.cookie_count("example.com") == 10

    def test_expired_jar_is_replaced(self):
        mgr = DomainCookieJar(CookieJarConfig(ttl_seconds=0.01))
        jar1 = mgr.get_jar("example.com")
        time.sleep(0.05)
        jar2 = mgr.get_jar("example.com")
        assert jar1 is not jar2

    def test_no_expiry_when_ttl_none(self):
        mgr = DomainCookieJar(CookieJarConfig(ttl_seconds=None))
        jar1 = mgr.get_jar("example.com")
        time.sleep(0.01)
        jar2 = mgr.get_jar("example.com")
        assert jar1 is jar2

    def test_global_jar_when_not_isolated(self):
        mgr = DomainCookieJar(CookieJarConfig(isolate_by_domain=False))
        jar1 = mgr.get_jar("a.com")
        jar2 = mgr.get_jar("b.com")
        assert jar1 is jar2
        assert mgr.domain_count() == 1
