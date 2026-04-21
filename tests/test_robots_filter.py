"""Tests for scrapewarden.robots_filter."""

from unittest.mock import MagicMock, patch

import pytest

from scrapewarden.robots_filter import RobotsConfig, RobotsFilter


class TestRobotsConfig:
    def test_defaults(self):
        cfg = RobotsConfig()
        assert cfg.user_agent == "*"
        assert cfg.respect_robots is True
        assert cfg.cache_ttl == 3600

    def test_from_dict(self):
        cfg = RobotsConfig.from_dict(
            {"user_agent": "MyBot", "respect_robots": False, "cache_ttl": "600"}
        )
        assert cfg.user_agent == "MyBot"
        assert cfg.respect_robots is False
        assert cfg.cache_ttl == 600

    def test_from_dict_defaults(self):
        cfg = RobotsConfig.from_dict({})
        assert cfg.user_agent == "*"
        assert cfg.respect_robots is True
        assert cfg.cache_ttl == 3600


class TestRobotsFilter:
    @pytest.fixture()
    def filter_(self):
        return RobotsFilter(RobotsConfig(user_agent="TestBot"))

    def _mock_parser(self, allowed: bool):
        parser = MagicMock()
        parser.can_fetch.return_value = allowed
        return parser

    def test_allowed_when_respect_disabled(self):
        rf = RobotsFilter(RobotsConfig(respect_robots=False))
        # No network call should happen; always allowed
        assert rf.is_allowed("http://example.com/secret") is True

    def test_allowed_url(self, filter_):
        with patch.object(filter_, "_get_parser", return_value=self._mock_parser(True)):
            assert filter_.is_allowed("http://example.com/page") is True

    def test_disallowed_url(self, filter_):
        with patch.object(filter_, "_get_parser", return_value=self._mock_parser(False)):
            assert filter_.is_allowed("http://example.com/private") is False

    def test_allows_when_parser_unavailable(self, filter_):
        with patch.object(filter_, "_get_parser", return_value=None):
            assert filter_.is_allowed("http://example.com/anything") is True

    def test_cache_populated_after_fetch(self, filter_):
        with patch("scrapewarden.robots_filter.RobotFileParser") as MockParser:
            instance = MockParser.return_value
            instance.can_fetch.return_value = True
            filter_.is_allowed("http://example.com/page")
            assert filter_.cached_domains == 1

    def test_cache_reused_within_ttl(self, filter_):
        with patch("scrapewarden.robots_filter.RobotFileParser") as MockParser:
            instance = MockParser.return_value
            instance.can_fetch.return_value = True
            filter_.is_allowed("http://example.com/a")
            filter_.is_allowed("http://example.com/b")
            # read() should only be called once (cache hit on second call)
            assert instance.read.call_count == 1

    def test_clear_cache(self, filter_):
        with patch("scrapewarden.robots_filter.RobotFileParser") as MockParser:
            instance = MockParser.return_value
            instance.can_fetch.return_value = True
            filter_.is_allowed("http://example.com/page")
            assert filter_.cached_domains == 1
            filter_.clear_cache()
            assert filter_.cached_domains == 0

    def test_robots_url_extraction(self, filter_):
        url = filter_._robots_url("https://example.com/some/deep/path?q=1")
        assert url == "https://example.com/robots.txt"
