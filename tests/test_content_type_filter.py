"""Tests for ContentTypeFilter."""
import pytest
from scrapewarden.content_type_filter import ContentTypeConfig, ContentTypeFilter


@pytest.fixture()
def default_filter() -> ContentTypeFilter:
    return ContentTypeFilter()


class TestContentTypeConfig:
    def test_defaults(self):
        cfg = ContentTypeConfig()
        assert "text/html" in cfg.allowed_types
        assert "application/json" in cfg.allowed_types
        assert "image/png" in cfg.blocked_types
        assert cfg.strict is False

    def test_from_dict_custom_allowed(self):
        cfg = ContentTypeConfig.from_dict({"allowed_types": ["text/html"]})
        assert cfg.allowed_types == ["text/html"]

    def test_from_dict_strict(self):
        cfg = ContentTypeConfig.from_dict({"strict": True})
        assert cfg.strict is True

    def test_from_dict_defaults(self):
        cfg = ContentTypeConfig.from_dict({})
        assert cfg.allowed_types  # non-empty
        assert cfg.strict is False


class TestContentTypeFilter:
    def test_html_allowed_by_default(self, default_filter):
        assert default_filter.is_allowed("text/html") is True

    def test_json_allowed_by_default(self, default_filter):
        assert default_filter.is_allowed("application/json") is True

    def test_image_blocked_by_default(self, default_filter):
        assert default_filter.is_allowed("image/png") is False

    def test_zip_blocked_by_default(self, default_filter):
        assert default_filter.is_blocked("application/zip") is True

    def test_charset_param_stripped(self, default_filter):
        assert default_filter.is_allowed("text/html; charset=utf-8") is True

    def test_case_insensitive(self, default_filter):
        assert default_filter.is_allowed("TEXT/HTML") is True
        assert default_filter.is_blocked("IMAGE/PNG") is True

    def test_unknown_type_allowed_in_non_strict(self, default_filter):
        assert default_filter.is_allowed("application/x-custom") is True

    def test_unknown_type_blocked_in_strict_mode(self):
        cfg = ContentTypeConfig.from_dict({"strict": True})
        f = ContentTypeFilter(cfg)
        assert f.is_allowed("application/x-custom") is False

    def test_strict_allows_explicitly_listed(self):
        cfg = ContentTypeConfig.from_dict(
            {"allowed_types": ["text/html", "application/json"], "strict": True}
        )
        f = ContentTypeFilter(cfg)
        assert f.is_allowed("text/html") is True
        assert f.is_allowed("text/plain") is False

    def test_classify_allowed(self, default_filter):
        assert default_filter.classify("text/html") == "allowed"

    def test_classify_blocked(self, default_filter):
        assert default_filter.classify("image/jpeg") == "blocked"

    def test_classify_unknown(self, default_filter):
        assert default_filter.classify("application/x-mystery") == "unknown"

    def test_classify_unknown_strict(self):
        cfg = ContentTypeConfig.from_dict({"strict": True})
        f = ContentTypeFilter(cfg)
        assert f.classify("application/x-mystery") == "blocked"
