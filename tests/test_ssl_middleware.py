"""Tests for SSLMiddleware."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from scrapewarden.ssl_middleware import SSLMiddleware
from scrapewarden.ssl_verifier import SSLVerifierConfig, SSLVerificationResult


@pytest.fixture
def mw():
    return SSLMiddleware()


class TestSSLMiddlewareInit:
    def test_from_dict_creates_instance(self):
        m = SSLMiddleware.from_dict({"enabled": True, "timeout": 3.0})
        assert isinstance(m, SSLMiddleware)
        assert m.config.timeout == 3.0

    def test_default_from_dict(self):
        m = SSLMiddleware.from_dict({})
        assert m.config.enabled is True

    def test_initial_block_count_zero(self, mw):
        assert mw.block_count == 0

    def test_initial_blocked_domains_empty(self, mw):
        assert mw.blocked_domains == []


class TestSSLMiddlewareBehavior:
    def test_allows_verified_domain(self, mw):
        with patch.object(mw._verifier, "_get_cert_fingerprint", return_value="fp"):
            assert mw.on_request("example.com") is True

    def test_blocks_unverified_domain(self, mw):
        with patch.object(mw._verifier, "_get_cert_fingerprint", return_value=None):
            assert mw.on_request("bad.example.com") is False

    def test_blocked_domain_recorded(self, mw):
        with patch.object(mw._verifier, "_get_cert_fingerprint", return_value=None):
            mw.on_request("bad.example.com")
        assert "bad.example.com" in mw.blocked_domains

    def test_block_count_increments(self, mw):
        with patch.object(mw._verifier, "_get_cert_fingerprint", return_value=None):
            mw.on_request("a.com")
            mw.on_request("b.com")
        assert mw.block_count == 2

    def test_same_domain_not_duplicated_in_blocked(self, mw):
        with patch.object(mw._verifier, "_get_cert_fingerprint", return_value=None):
            mw.on_request("bad.com")
            mw.on_request("bad.com")
        assert mw.blocked_domains.count("bad.com") == 1

    def test_last_result_stored(self, mw):
        with patch.object(mw._verifier, "_get_cert_fingerprint", return_value="fp"):
            mw.on_request("example.com")
        result = mw.last_result("example.com")
        assert result is not None
        assert result.domain == "example.com"

    def test_last_result_none_for_unseen(self, mw):
        assert mw.last_result("unseen.com") is None

    def test_disabled_allows_all(self):
        m = SSLMiddleware(SSLVerifierConfig(enabled=False))
        assert m.on_request("anything.com") is True

    def test_reset_clears_state(self, mw):
        with patch.object(mw._verifier, "_get_cert_fingerprint", return_value=None):
            mw.on_request("bad.com")
        mw.reset()
        assert mw.block_count == 0
        assert mw.blocked_domains == []
        assert mw.last_result("bad.com") is None
