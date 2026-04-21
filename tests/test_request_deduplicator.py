"""Tests for RequestDeduplicator."""

import pytest

from scrapewarden.request_deduplicator import DeduplicatorConfig, RequestDeduplicator


class TestDeduplicatorConfig:
    def test_defaults(self):
        cfg = DeduplicatorConfig()
        assert cfg.max_size == 100_000

    def test_from_dict(self):
        cfg = DeduplicatorConfig.from_dict({"max_size": 500})
        assert cfg.max_size == 500

    def test_from_dict_defaults(self):
        cfg = DeduplicatorConfig.from_dict({})
        assert cfg.max_size == 100_000


class TestRequestDeduplicator:
    @pytest.fixture
    def dedup(self):
        return RequestDeduplicator()

    def test_new_url_not_seen(self, dedup):
        assert dedup.is_seen("https://example.com/page") is False

    def test_mark_seen_records_url(self, dedup):
        dedup.mark_seen("https://example.com/page")
        assert dedup.is_seen("https://example.com/page") is True

    def test_different_url_not_seen(self, dedup):
        dedup.mark_seen("https://example.com/page1")
        assert dedup.is_seen("https://example.com/page2") is False

    def test_check_and_mark_returns_false_first_time(self, dedup):
        result = dedup.check_and_mark("https://example.com/a")
        assert result is False

    def test_check_and_mark_returns_true_second_time(self, dedup):
        dedup.check_and_mark("https://example.com/a")
        result = dedup.check_and_mark("https://example.com/a")
        assert result is True

    def test_method_differentiates_requests(self, dedup):
        dedup.mark_seen("https://example.com/resource", method="GET")
        assert dedup.is_seen("https://example.com/resource", method="POST") is False

    def test_body_differentiates_post_requests(self, dedup):
        dedup.mark_seen("https://example.com/submit", method="POST", body=b"a=1")
        assert (
            dedup.is_seen("https://example.com/submit", method="POST", body=b"a=2")
            is False
        )

    def test_clear_resets_state(self, dedup):
        dedup.mark_seen("https://example.com/x")
        dedup.clear()
        assert dedup.is_seen("https://example.com/x") is False
        assert dedup.size == 0

    def test_size_tracks_entries(self, dedup):
        assert dedup.size == 0
        dedup.mark_seen("https://example.com/1")
        dedup.mark_seen("https://example.com/2")
        assert dedup.size == 2

    def test_duplicate_mark_does_not_grow_size(self, dedup):
        dedup.mark_seen("https://example.com/dup")
        dedup.mark_seen("https://example.com/dup")
        assert dedup.size == 1

    def test_max_size_evicts_entry(self):
        cfg = DeduplicatorConfig(max_size=3)
        dedup = RequestDeduplicator(cfg)
        for i in range(3):
            dedup.mark_seen(f"https://example.com/{i}")
        assert dedup.size == 3
        dedup.mark_seen("https://example.com/overflow")
        assert dedup.size == 3
