"""Tests for RequestTagger and TagMiddleware."""
import pytest

from scrapewarden.request_tagger import RequestTagger, TaggerConfig
from scrapewarden.tag_middleware import TagMiddleware


# ---------------------------------------------------------------------------
# TaggerConfig
# ---------------------------------------------------------------------------

class TestTaggerConfig:
    def test_defaults(self):
        cfg = TaggerConfig()
        assert cfg.default_tags == {}
        assert cfg.domain_tags == {}
        assert cfg.tag_header == "X-ScrapeWarden-Tags"
        assert cfg.include_in_headers is True
        assert cfg.max_tags_per_request == 20

    def test_from_dict(self):
        cfg = TaggerConfig.from_dict({
            "default_tags": {"env": "prod"},
            "domain_tags": {"example.com": {"tier": "gold"}},
            "tag_header": "X-Tags",
            "include_in_headers": False,
            "max_tags_per_request": 5,
        })
        assert cfg.default_tags == {"env": "prod"}
        assert cfg.domain_tags["example.com"] == {"tier": "gold"}
        assert cfg.tag_header == "X-Tags"
        assert cfg.include_in_headers is False
        assert cfg.max_tags_per_request == 5

    def test_from_dict_defaults(self):
        cfg = TaggerConfig.from_dict({})
        assert cfg.max_tags_per_request == 20


# ---------------------------------------------------------------------------
# RequestTagger
# ---------------------------------------------------------------------------

@pytest.fixture
def tagger():
    cfg = TaggerConfig(
        default_tags={"project": "test"},
        domain_tags={"example.com": {"site": "example"}},
    )
    return RequestTagger(config=cfg)


class TestRequestTagger:
    def test_tag_request_merges_defaults(self, tagger):
        tags = tagger.tag_request("req-1", "other.com")
        assert tags["project"] == "test"

    def test_tag_request_merges_domain_tags(self, tagger):
        tags = tagger.tag_request("req-2", "example.com")
        assert tags["site"] == "example"
        assert tags["project"] == "test"

    def test_extra_tags_override(self, tagger):
        tags = tagger.tag_request("req-3", "example.com", extra={"project": "override"})
        assert tags["project"] == "override"

    def test_get_tags_returns_stored(self, tagger):
        tagger.tag_request("req-4", "example.com")
        assert tagger.get_tags("req-4")["site"] == "example"

    def test_get_tags_missing_returns_empty(self, tagger):
        assert tagger.get_tags("nonexistent") == {}

    def test_clear_removes_entry(self, tagger):
        tagger.tag_request("req-5", "example.com")
        tagger.clear("req-5")
        assert tagger.get_tags("req-5") == {}

    def test_max_tags_enforced(self):
        cfg = TaggerConfig(default_tags={str(i): str(i) for i in range(25)}, max_tags_per_request=10)
        t = RequestTagger(config=cfg)
        tags = t.tag_request("req-x", "example.com")
        assert len(tags) == 10

    def test_build_header_format(self, tagger):
        header = tagger.build_header({"a": "1", "b": "2"})
        assert "a=1" in header
        assert "b=2" in header

    def test_tracked_count(self, tagger):
        tagger.tag_request("r1", "example.com")
        tagger.tag_request("r2", "example.com")
        assert tagger.tracked_count == 2


# ---------------------------------------------------------------------------
# TagMiddleware
# ---------------------------------------------------------------------------

@pytest.fixture
def mw():
    return TagMiddleware.from_dict({"default_tags": {"env": "ci"}})


class TestTagMiddleware:
    def test_from_dict_creates_instance(self):
        m = TagMiddleware.from_dict({})
        assert isinstance(m, TagMiddleware)

    def test_on_request_injects_header(self, mw):
        headers = mw.on_request("r1", "example.com", {})
        assert "X-ScrapeWarden-Tags" in headers
        assert "env=ci" in headers["X-ScrapeWarden-Tags"]

    def test_on_request_no_header_when_disabled(self):
        m = TagMiddleware.from_dict({"default_tags": {"x": "y"}, "include_in_headers": False})
        headers = m.on_request("r1", "example.com", {})
        assert "X-ScrapeWarden-Tags" not in headers

    def test_tagged_count_increments(self, mw):
        mw.on_request("r1", "example.com", {})
        mw.on_request("r2", "example.com", {})
        assert mw.tagged_count == 2

    def test_on_response_clears_pending(self, mw):
        mw.on_request("r1", "example.com", {})
        assert mw.pending_count == 1
        mw.on_response("r1")
        assert mw.pending_count == 0
