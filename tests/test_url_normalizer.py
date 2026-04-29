"""Tests for url_normalizer and normalize_middleware."""

import pytest

from scrapewarden.url_normalizer import NormalizerConfig, URLNormalizer
from scrapewarden.normalize_middleware import NormalizeMiddleware


# ---------------------------------------------------------------------------
# NormalizerConfig
# ---------------------------------------------------------------------------

class TestNormalizerConfig:
    def test_defaults(self):
        cfg = NormalizerConfig()
        assert cfg.sort_query_params is True
        assert cfg.remove_fragments is True
        assert cfg.lowercase_host is True
        assert cfg.strip_trailing_slash is True
        assert cfg.remove_default_ports is True
        assert cfg.drop_params == []

    def test_from_dict(self):
        cfg = NormalizerConfig.from_dict({"sort_query_params": False, "drop_params": ["utm_source"]})
        assert cfg.sort_query_params is False
        assert cfg.drop_params == ["utm_source"]

    def test_from_dict_defaults(self):
        cfg = NormalizerConfig.from_dict({})
        assert cfg.remove_fragments is True


# ---------------------------------------------------------------------------
# URLNormalizer
# ---------------------------------------------------------------------------

@pytest.fixture
def normalizer():
    return URLNormalizer()


class TestURLNormalizer:
    def test_lowercase_host(self, normalizer):
        assert normalizer.normalize("https://EXAMPLE.COM/path") == "https://example.com/path"

    def test_removes_default_port_http(self, normalizer):
        assert normalizer.normalize("http://example.com:80/") == "http://example.com"

    def test_removes_default_port_https(self, normalizer):
        assert normalizer.normalize("https://example.com:443/page") == "https://example.com/page"

    def test_keeps_non_default_port(self, normalizer):
        result = normalizer.normalize("https://example.com:8443/page")
        assert ":8443" in result

    def test_strips_trailing_slash(self, normalizer):
        assert normalizer.normalize("https://example.com/path/") == "https://example.com/path"

    def test_root_slash_preserved(self, normalizer):
        # single slash is the path itself — stripping would produce empty path
        result = normalizer.normalize("https://example.com/")
        assert result == "https://example.com"

    def test_sorts_query_params(self, normalizer):
        url = "https://example.com/search?z=1&a=2"
        assert normalizer.normalize(url) == "https://example.com/search?a=2&z=1"

    def test_removes_fragment(self, normalizer):
        assert "#" not in normalizer.normalize("https://example.com/page#section")

    def test_drop_params(self):
        cfg = NormalizerConfig.from_dict({"drop_params": ["utm_source", "utm_medium"]})
        n = URLNormalizer(cfg)
        result = n.normalize("https://example.com/?utm_source=email&q=hello")
        assert "utm_source" not in result
        assert "q=hello" in result

    def test_are_equivalent_true(self, normalizer):
        a = "https://EXAMPLE.COM:443/path/?b=2&a=1#frag"
        b = "https://example.com/path?a=1&b=2"
        assert normalizer.are_equivalent(a, b)

    def test_are_equivalent_false(self, normalizer):
        assert not normalizer.are_equivalent("https://example.com/a", "https://example.com/b")


# ---------------------------------------------------------------------------
# NormalizeMiddleware
# ---------------------------------------------------------------------------

@pytest.fixture
def mw():
    return NormalizeMiddleware()


class TestNormalizeMiddleware:
    def test_from_dict_creates_instance(self):
        m = NormalizeMiddleware.from_dict({"sort_query_params": True})
        assert isinstance(m, NormalizeMiddleware)

    def test_rewrites_url(self, mw):
        req = {"url": "HTTPS://EXAMPLE.COM:443/path/?z=1&a=2#frag"}
        result = mw.on_request(req)
        assert result["url"] == "https://example.com/path?a=2&z=1"

    def test_increments_rewrite_count(self, mw):
        mw.on_request({"url": "HTTPS://EXAMPLE.COM/"})
        assert mw.rewrite_count == 1

    def test_no_rewrite_when_already_normal(self, mw):
        mw.on_request({"url": "https://example.com/path"})
        assert mw.rewrite_count == 0

    def test_history_recorded(self, mw):
        mw.on_request({"url": "HTTP://EXAMPLE.COM:80/"})
        assert len(mw.history) == 1
        assert mw.history[0]["original"] == "HTTP://EXAMPLE.COM:80/"

    def test_reset_clears_state(self, mw):
        mw.on_request({"url": "HTTP://EXAMPLE.COM/"})
        mw.reset()
        assert mw.rewrite_count == 0
        assert mw.history == []
