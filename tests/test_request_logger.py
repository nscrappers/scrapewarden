"""Tests for scrapewarden.request_logger."""

import time
import pytest
from scrapewarden.request_logger import RequestLogConfig, RequestLogger, RequestLogEntry


class TestRequestLogConfig:
    def test_defaults(self):
        cfg = RequestLogConfig()
        assert cfg.enabled is True
        assert cfg.log_request_headers is False
        assert cfg.log_response_headers is False
        assert cfg.log_body_preview is False
        assert cfg.body_preview_length == 200
        assert cfg.level == "INFO"

    def test_from_dict(self):
        cfg = RequestLogConfig.from_dict({
            "enabled": False,
            "log_request_headers": True,
            "log_response_headers": True,
            "log_body_preview": True,
            "body_preview_length": 50,
            "level": "DEBUG",
        })
        assert cfg.enabled is False
        assert cfg.log_request_headers is True
        assert cfg.body_preview_length == 50
        assert cfg.level == "DEBUG"

    def test_from_dict_defaults(self):
        cfg = RequestLogConfig.from_dict({})
        assert cfg.enabled is True
        assert cfg.level == "INFO"


class TestRequestLogger:
    @pytest.fixture
    def logger(self):
        return RequestLogger(RequestLogConfig(enabled=True, log_body_preview=True, body_preview_length=10))

    def test_log_request_returns_timestamp(self, logger):
        before = time.monotonic()
        ts = logger.log_request("GET", "https://example.com")
        after = time.monotonic()
        assert before <= ts <= after

    def test_log_response_returns_entry(self, logger):
        ts = logger.log_request("GET", "https://example.com")
        entry = logger.log_response("GET", "https://example.com", 200, ts)
        assert isinstance(entry, RequestLogEntry)
        assert entry.status_code == 200
        assert entry.elapsed_ms is not None
        assert entry.elapsed_ms >= 0

    def test_log_response_body_preview(self, logger):
        ts = logger.log_request("POST", "https://example.com")
        body = b"Hello, World! This is a long body."
        entry = logger.log_response("POST", "https://example.com", 201, ts, body=body)
        assert entry.body_preview == "Hello, Wor"

    def test_log_error_returns_entry(self, logger):
        ts = logger.log_request("GET", "https://example.com")
        entry = logger.log_error("GET", "https://example.com", "ConnectionError", ts)
        assert entry.error == "ConnectionError"
        assert entry.status_code is None
        assert entry.elapsed_ms >= 0

    def test_proxy_recorded(self, logger):
        ts = logger.log_request("GET", "https://example.com", proxy="http://proxy:8080")
        entry = logger.log_response("GET", "https://example.com", 200, ts, proxy="http://proxy:8080")
        assert entry.proxy == "http://proxy:8080"

    def test_disabled_logger_still_returns_entry(self):
        rl = RequestLogger(RequestLogConfig(enabled=False))
        ts = rl.log_request("GET", "https://example.com")
        entry = rl.log_response("GET", "https://example.com", 404, ts)
        assert entry.status_code == 404

    def test_to_dict_shape(self, logger):
        ts = logger.log_request("GET", "https://example.com")
        entry = logger.log_response("GET", "https://example.com", 200, ts)
        d = entry.to_dict()
        assert set(d.keys()) == {"method", "url", "status_code", "elapsed_ms", "proxy", "error"}

    def test_response_headers_captured(self):
        rl = RequestLogger(RequestLogConfig(log_response_headers=True))
        ts = rl.log_request("GET", "https://example.com")
        headers = {"Content-Type": "application/json"}
        entry = rl.log_response("GET", "https://example.com", 200, ts, headers=headers)
        assert entry.response_headers == headers
