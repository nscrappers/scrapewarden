"""Tests for RequestSigner and SignerConfig."""
import pytest
from scrapewarden.request_signer import RequestSigner, SignerConfig


class TestSignerConfig:
    def test_defaults(self):
        cfg = SignerConfig()
        assert cfg.algorithm == "sha256"
        assert cfg.include_timestamp is True
        assert cfg.signature_header == "X-Signature"
        assert cfg.timestamp_header == "X-Timestamp"
        assert cfg.extra_headers_to_sign == []

    def test_from_dict(self):
        cfg = SignerConfig.from_dict({"secret_key": "abc", "algorithm": "sha512"})
        assert cfg.secret_key == "abc"
        assert cfg.algorithm == "sha512"

    def test_from_dict_defaults(self):
        cfg = SignerConfig.from_dict({})
        assert cfg.secret_key == ""
        assert cfg.include_timestamp is True


class TestRequestSigner:
    @pytest.fixture
    def signer(self):
        return RequestSigner(SignerConfig(secret_key="test-secret"))

    def test_sign_returns_signature_header(self, signer):
        headers = signer.sign("GET", "https://example.com/page")
        assert "X-Signature" in headers

    def test_sign_includes_timestamp(self, signer):
        headers = signer.sign("GET", "https://example.com/page")
        assert "X-Timestamp" in headers

    def test_sign_no_timestamp_when_disabled(self):
        cfg = SignerConfig(secret_key="s", include_timestamp=False)
        s = RequestSigner(cfg)
        headers = s.sign("GET", "https://example.com")
        assert "X-Timestamp" not in headers
        assert "X-Signature" in headers

    def test_verify_valid_signature(self, signer):
        signed = signer.sign("POST", "https://api.example.com/data")
        assert signer.verify("POST", "https://api.example.com/data", signed) is True

    def test_verify_invalid_signature(self, signer):
        signed = signer.sign("POST", "https://api.example.com/data")
        signed["X-Signature"] = "badsig"
        assert signer.verify("POST", "https://api.example.com/data", signed) is False

    def test_verify_wrong_method(self, signer):
        signed = signer.sign("GET", "https://example.com")
        assert signer.verify("POST", "https://example.com", signed) is False

    def test_verify_no_secret_returns_false(self):
        cfg = SignerConfig(secret_key="")
        s = RequestSigner(cfg)
        assert s.verify("GET", "https://example.com", {}) is False

    def test_different_urls_produce_different_sigs(self, signer):
        h1 = signer.sign("GET", "https://example.com/a")
        h2 = signer.sign("GET", "https://example.com/b")
        assert h1["X-Signature"] != h2["X-Signature"]

    def test_extra_headers_affect_signature(self):
        cfg = SignerConfig(secret_key="s", include_timestamp=False, extra_headers_to_sign=["X-User"])
        s = RequestSigner(cfg)
        h1 = s.sign("GET", "https://example.com", {"X-User": "alice"})
        h2 = s.sign("GET", "https://example.com", {"X-User": "bob"})
        assert h1["X-Signature"] != h2["X-Signature"]
