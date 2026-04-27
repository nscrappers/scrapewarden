"""Tests for ErrorClassifier and ErrorClassifierConfig."""
import ssl
import pytest

from scrapewarden.error_classifier import (
    ErrorClass,
    ErrorClassifier,
    ErrorClassifierConfig,
)


@pytest.fixture
def classifier() -> ErrorClassifier:
    return ErrorClassifier()


class TestErrorClassifierConfig:
    def test_defaults(self):
        cfg = ErrorClassifierConfig()
        assert "ConnectionError" in cfg.network_exceptions
        assert "TimeoutError" in cfg.timeout_exceptions
        assert "ssl.SSLError" in cfg.ssl_exceptions

    def test_from_dict_custom(self):
        cfg = ErrorClassifierConfig.from_dict(
            {"network_exceptions": ["MyNetworkError"]}
        )
        assert cfg.network_exceptions == ["MyNetworkError"]
        # other fields keep defaults
        assert "TimeoutError" in cfg.timeout_exceptions

    def test_from_dict_empty(self):
        cfg = ErrorClassifierConfig.from_dict({})
        assert isinstance(cfg.proxy_exceptions, list)


class TestErrorClassifier:
    def test_classifies_connection_error(self, classifier):
        assert classifier.classify(ConnectionError()) == ErrorClass.NETWORK

    def test_classifies_timeout_error(self, classifier):
        assert classifier.classify(TimeoutError()) == ErrorClass.TIMEOUT

    def test_classifies_broken_pipe(self, classifier):
        assert classifier.classify(BrokenPipeError()) == ErrorClass.NETWORK

    def test_classifies_ssl_error(self, classifier):
        exc = ssl.SSLError("bad cert")
        assert classifier.classify(exc) == ErrorClass.SSL

    def test_unknown_exception(self, classifier):
        assert classifier.classify(ValueError("oops")) == ErrorClass.UNKNOWN

    def test_classify_by_name_known(self, classifier):
        assert classifier.classify_by_name("TimeoutError") == ErrorClass.TIMEOUT

    def test_classify_by_name_unknown(self, classifier):
        assert classifier.classify_by_name("WeirdError") == ErrorClass.UNKNOWN

    def test_custom_config(self):
        cfg = ErrorClassifierConfig(proxy_exceptions=["MyProxyError"])
        clf = ErrorClassifier(cfg)
        assert clf.classify_by_name("MyProxyError") == ErrorClass.PROXY
