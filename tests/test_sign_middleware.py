"""Tests for SignMiddleware."""
import pytest
from scrapewarden.sign_middleware import SignMiddleware


@pytest.fixture
def mw():
    return SignMiddleware.from_dict({"secret_key": "middleware-secret", "include_timestamp": False})


class TestSignMiddlewareInit:
    def test_from_dict_creates_instance(self):
        m = SignMiddleware.from_dict({"secret_key": "k"})
        assert isinstance(m, SignMiddleware)

    def test_default_from_dict(self):
        m = SignMiddleware.from_dict({})
        assert m.signed_count == 0


class TestSignMiddlewareBehavior:
    def test_on_request_adds_signature(self, mw):
        headers = mw.on_request("GET", "https://example.com")
        assert "X-Signature" in headers

    def test_on_request_increments_count(self, mw):
        mw.on_request("GET", "https://example.com")
        mw.on_request("POST", "https://example.com/api")
        assert mw.signed_count == 2

    def test_on_request_preserves_existing_headers(self, mw):
        headers = mw.on_request("GET", "https://example.com", {"Authorization": "Bearer token"})
        assert headers["Authorization"] == "Bearer token"
        assert "X-Signature" in headers

    def test_reset_clears_count(self, mw):
        mw.on_request("GET", "https://example.com")
        mw.reset()
        assert mw.signed_count == 0

    def test_verify_response_headers_valid(self, mw):
        headers = mw.on_request("GET", "https://example.com/path")
        assert mw.verify_response_headers("GET", "https://example.com/path", headers) is True

    def test_verify_response_headers_invalid(self, mw):
        headers = {"X-Signature": "fakesig"}
        assert mw.verify_response_headers("GET", "https://example.com", headers) is False

    def test_signed_count_initial_zero(self, mw):
        assert mw.signed_count == 0
