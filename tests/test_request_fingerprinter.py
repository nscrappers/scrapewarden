"""Tests for RequestFingerprinter and FingerprintConfig."""

import pytest
from scrapewarden.request_fingerprinter import FingerprintConfig, RequestFingerprinter


class TestRequestFingerprinter:
    def _fp(self, **kwargs) -> RequestFingerprinter:
        config = FingerprintConfig(**kwargs)
        return RequestFingerprinter(config)

    def test_same_url_same_fingerprint(self):
        fp = RequestFingerprinter()
        a = fp.fingerprint("https://example.com/page")
        b = fp.fingerprint("https://example.com/page")
        assert a == b

    def test_different_urls_different_fingerprints(self):
        fp = RequestFingerprinter()
        a = fp.fingerprint("https://example.com/a")
        b = fp.fingerprint("https://example.com/b")
        assert a != b

    def test_method_affects_fingerprint(self):
        fp = RequestFingerprinter()
        get = fp.fingerprint("https://example.com/", method="GET")
        post = fp.fingerprint("https://example.com/", method="POST")
        assert get != post

    def test_body_affects_fingerprint(self):
        fp = RequestFingerprinter()
        a = fp.fingerprint("https://example.com/", body=b"foo")
        b = fp.fingerprint("https://example.com/", body=b"bar")
        assert a != b

    def test_query_param_order_normalized(self):
        fp = RequestFingerprinter()
        a = fp.fingerprint("https://example.com/?z=1&a=2")
        b = fp.fingerprint("https://example.com/?a=2&z=1")
        assert a == b

    def test_ignored_query_params(self):
        fp = self._fp(ignore_query_params={"utm_source", "utm_medium"})
        a = fp.fingerprint("https://example.com/?q=hello&utm_source=email")
        b = fp.fingerprint("https://example.com/?q=hello")
        assert a == b

    def test_ignored_params_do_not_affect_others(self):
        fp = self._fp(ignore_query_params={"session"})
        a = fp.fingerprint("https://example.com/?q=a&session=xyz")
        b = fp.fingerprint("https://example.com/?q=b&session=xyz")
        assert a != b

    def test_include_headers_changes_fingerprint(self):
        fp = self._fp(include_headers={"x-api-key"})
        a = fp.fingerprint("https://example.com/", headers={"x-api-key": "key1"})
        b = fp.fingerprint("https://example.com/", headers={"x-api-key": "key2"})
        assert a != b

    def test_untracked_headers_ignored(self):
        fp = RequestFingerprinter()
        a = fp.fingerprint("https://example.com/", headers={"User-Agent": "bot/1"})
        b = fp.fingerprint("https://example.com/", headers={"User-Agent": "bot/2"})
        assert a == b

    def test_is_seen_and_mark_seen(self):
        fp = RequestFingerprinter()
        digest = fp.fingerprint("https://example.com/")
        assert not fp.is_seen(digest)
        fp.mark_seen(digest)
        assert fp.is_seen(digest)

    def test_seen_count_increments(self):
        fp = RequestFingerprinter()
        assert fp.seen_count() == 0
        fp.mark_seen(fp.fingerprint("https://example.com/a"))
        fp.mark_seen(fp.fingerprint("https://example.com/b"))
        assert fp.seen_count() == 2

    def test_reset_clears_seen(self):
        fp = RequestFingerprinter()
        digest = fp.fingerprint("https://example.com/")
        fp.mark_seen(digest)
        fp.reset()
        assert not fp.is_seen(digest)
        assert fp.seen_count() == 0

    def test_from_dict_config(self):
        config = FingerprintConfig.from_dict(
            {"ignore_query_params": ["sid"], "include_headers": ["Authorization"], "hash_algorithm": "md5"}
        )
        assert "sid" in config.ignore_query_params
        assert "authorization" in config.include_headers
        assert config.hash_algorithm == "md5"
