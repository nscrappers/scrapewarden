"""Tests for ErrorMiddleware and ErrorStats."""
import pytest

from scrapewarden.error_classifier import ErrorClass
from scrapewarden.error_middleware import ErrorMiddleware


@pytest.fixture
def mw() -> ErrorMiddleware:
    return ErrorMiddleware()


class TestErrorMiddlewareInit:
    def test_from_dict_creates_instance(self):
        instance = ErrorMiddleware.from_dict({})
        assert isinstance(instance, ErrorMiddleware)

    def test_default_stats_empty(self, mw):
        assert mw.summary() == {}


class TestErrorMiddlewareBehavior:
    def test_on_error_returns_class(self, mw):
        ec = mw.on_error("http://example.com/page", ConnectionError())
        assert ec == ErrorClass.NETWORK

    def test_on_error_records_domain(self, mw):
        mw.on_error("http://example.com/page", TimeoutError())
        stats = mw.stats.for_domain("example.com")
        assert stats.total == 1
        assert stats.counts[ErrorClass.TIMEOUT.value] == 1

    def test_multiple_errors_accumulate(self, mw):
        mw.on_error("http://example.com/a", ConnectionError())
        mw.on_error("http://example.com/b", ConnectionError())
        mw.on_error("http://example.com/c", TimeoutError())
        stats = mw.stats.for_domain("example.com")
        assert stats.total == 3
        assert stats.counts[ErrorClass.NETWORK.value] == 2

    def test_rate_calculation(self, mw):
        mw.on_error("http://example.com/a", TimeoutError())
        mw.on_error("http://example.com/b", TimeoutError())
        mw.on_error("http://example.com/c", ConnectionError())
        rate = mw.stats.rate_for_domain("example.com", ErrorClass.TIMEOUT)
        assert abs(rate - 2 / 3) < 1e-9

    def test_different_domains_isolated(self, mw):
        mw.on_error("http://site-a.com/x", TimeoutError())
        mw.on_error("http://site-b.com/y", ConnectionError())
        assert mw.stats.total_for_domain("site-a.com") == 1
        assert mw.stats.total_for_domain("site-b.com") == 1

    def test_summary_contains_domains(self, mw):
        mw.on_error("http://example.com/a", ValueError())
        summary = mw.summary()
        assert "example.com" in summary
        assert summary["example.com"]["total"] == 1
