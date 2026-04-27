import pytest
from scrapewarden.validation_middleware import ValidationMiddleware
from scrapewarden.response_validator import ValidationResult


@pytest.fixture
def mw():
    return ValidationMiddleware.from_dict({})


class TestValidationMiddlewareInit:
    def test_from_dict_creates_instance(self):
        m = ValidationMiddleware.from_dict({"min_body_length": 10})
        assert isinstance(m, ValidationMiddleware)

    def test_default_from_dict(self, mw):
        assert mw.valid_count == 0
        assert mw.invalid_count == 0


class TestValidationMiddlewareBehavior:
    def test_valid_response_increments_valid_count(self, mw):
        mw.on_response("http://example.com", "hello world")
        assert mw.valid_count == 1
        assert mw.invalid_count == 0

    def test_invalid_response_increments_invalid_count(self):
        m = ValidationMiddleware.from_dict({"min_body_length": 100})
        m.on_response("http://example.com", "short")
        assert m.invalid_count == 1
        assert m.valid_count == 0

    def test_invalid_responses_list_populated(self):
        m = ValidationMiddleware.from_dict({"forbidden_patterns": ["block"]})
        m.on_response("http://example.com/page", "you are blocked")
        assert len(m.invalid_responses) == 1
        assert m.invalid_responses[0]["url"] == "http://example.com/page"

    def test_on_invalid_callback_called(self):
        m = ValidationMiddleware.from_dict({"min_body_length": 50})
        calls = []
        m.on_response("http://x.com", "tiny", on_invalid=lambda u, r: calls.append(u))
        assert calls == ["http://x.com"]

    def test_on_invalid_callback_not_called_on_valid(self, mw):
        calls = []
        mw.on_response("http://x.com", "good content", on_invalid=lambda u, r: calls.append(u))
        assert calls == []

    def test_stats_returns_correct_dict(self):
        m = ValidationMiddleware.from_dict({"min_body_length": 100})
        m.on_response("http://a.com", "x" * 200)
        m.on_response("http://b.com", "short")
        s = m.stats()
        assert s["total"] == 2
        assert s["valid"] == 1
        assert s["invalid"] == 1
        assert s["invalid_rate"] == pytest.approx(0.5)

    def test_stats_zero_total(self, mw):
        s = mw.stats()
        assert s["total"] == 0
        assert s["invalid_rate"] == 0.0

    def test_reset_clears_counts(self):
        m = ValidationMiddleware.from_dict({"min_body_length": 100})
        m.on_response("http://a.com", "short")
        m.on_response("http://b.com", "x" * 200)
        m.reset()
        assert m.valid_count == 0
        assert m.invalid_count == 0
        assert m.invalid_responses == []
