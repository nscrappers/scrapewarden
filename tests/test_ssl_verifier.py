"""Tests for SSLVerifier and SSLVerifierConfig."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from scrapewarden.ssl_verifier import SSLVerifier, SSLVerifierConfig, SSLVerificationResult


class TestSSLVerifierConfig:
    def test_defaults(self):
        cfg = SSLVerifierConfig()
        assert cfg.enabled is True
        assert cfg.pin_certificates is False
        assert cfg.pinned_fingerprints == {}
        assert cfg.verify_hostname is True
        assert cfg.min_tls_version == "TLSv1.2"
        assert cfg.timeout == 10.0

    def test_from_dict(self):
        cfg = SSLVerifierConfig.from_dict({
            "enabled": False,
            "pin_certificates": True,
            "pinned_fingerprints": {"example.com": ["abc123"]},
            "timeout": 5.0,
        })
        assert cfg.enabled is False
        assert cfg.pin_certificates is True
        assert cfg.pinned_fingerprints == {"example.com": ["abc123"]}
        assert cfg.timeout == 5.0

    def test_from_dict_defaults(self):
        cfg = SSLVerifierConfig.from_dict({})
        assert cfg.enabled is True
        assert cfg.timeout == 10.0


@pytest.fixture
def verifier():
    return SSLVerifier(SSLVerifierConfig())


class TestSSLVerifier:
    def test_disabled_always_verified(self):
        cfg = SSLVerifierConfig(enabled=False)
        v = SSLVerifier(cfg)
        result = v.verify("example.com")
        assert result.verified is True

    def test_verify_returns_result_with_domain(self, verifier):
        with patch.object(verifier, "_get_cert_fingerprint", return_value="deadbeef"):
            result = verifier.verify("example.com")
        assert result.domain == "example.com"
        assert result.verified is True
        assert result.fingerprint == "deadbeef"

    def test_verify_fails_when_no_cert(self, verifier):
        with patch.object(verifier, "_get_cert_fingerprint", return_value=None):
            result = verifier.verify("bad.example.com")
        assert result.verified is False
        assert result.error is not None

    def test_pinning_blocks_unknown_fingerprint(self):
        cfg = SSLVerifierConfig(
            pin_certificates=True,
            pinned_fingerprints={"example.com": ["goodfp"]},
        )
        v = SSLVerifier(cfg)
        with patch.object(v, "_get_cert_fingerprint", return_value="badfp"):
            result = v.verify("example.com")
        assert result.verified is False
        assert "pinned" in result.error

    def test_pinning_allows_known_fingerprint(self):
        cfg = SSLVerifierConfig(
            pin_certificates=True,
            pinned_fingerprints={"example.com": ["goodfp"]},
        )
        v = SSLVerifier(cfg)
        with patch.object(v, "_get_cert_fingerprint", return_value="goodfp"):
            result = v.verify("example.com")
        assert result.verified is True

    def test_result_is_cached(self, verifier):
        with patch.object(verifier, "_get_cert_fingerprint", return_value="fp1") as mock_fp:
            verifier.verify("example.com")
            verifier.verify("example.com")
        mock_fp.assert_called_once()

    def test_clear_cache(self, verifier):
        with patch.object(verifier, "_get_cert_fingerprint", return_value="fp1"):
            verifier.verify("example.com")
        verifier.clear_cache()
        with patch.object(verifier, "_get_cert_fingerprint", return_value="fp2") as mock_fp:
            verifier.verify("example.com")
        mock_fp.assert_called_once()

    def test_is_verified_convenience(self, verifier):
        with patch.object(verifier, "_get_cert_fingerprint", return_value="fp"):
            assert verifier.is_verified("example.com") is True
