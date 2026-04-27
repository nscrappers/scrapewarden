import pytest
from scrapewarden.response_validator import (
    ValidatorConfig,
    ResponseValidator,
    ValidationResult,
)


@pytest.fixture
def default_validator():
    return ResponseValidator()


class TestValidatorConfig:
    def test_defaults(self):
        cfg = ValidatorConfig()
        assert cfg.min_body_length == 0
        assert cfg.required_patterns == []
        assert cfg.forbidden_patterns == []
        assert cfg.allowed_content_types == []
        assert cfg.require_utf8 is False

    def test_from_dict(self):
        cfg = ValidatorConfig.from_dict(
            {
                "min_body_length": 100,
                "required_patterns": ["hello"],
                "forbidden_patterns": ["error"],
                "allowed_content_types": ["text/html"],
                "require_utf8": True,
            }
        )
        assert cfg.min_body_length == 100
        assert cfg.required_patterns == ["hello"]
        assert cfg.forbidden_patterns == ["error"]
        assert cfg.allowed_content_types == ["text/html"]
        assert cfg.require_utf8 is True

    def test_from_dict_defaults(self):
        cfg = ValidatorConfig.from_dict({})
        assert cfg.min_body_length == 0


class TestResponseValidator:
    def test_empty_body_passes_default(self, default_validator):
        result = default_validator.validate("")
        assert result.valid is True

    def test_min_body_length_fail(self):
        v = ResponseValidator(ValidatorConfig(min_body_length=50))
        result = v.validate("short")
        assert result.valid is False
        assert "below minimum" in result.reason

    def test_min_body_length_pass(self):
        v = ResponseValidator(ValidatorConfig(min_body_length=5))
        result = v.validate("hello world")
        assert result.valid is True

    def test_required_pattern_missing(self):
        v = ResponseValidator(ValidatorConfig(required_patterns=["<title>"]))
        result = v.validate("<html><body></body></html>")
        assert result.valid is False
        assert "required pattern" in result.reason

    def test_required_pattern_present(self):
        v = ResponseValidator(ValidatorConfig(required_patterns=["<title>"]))
        result = v.validate("<html><title>Test</title></html>")
        assert result.valid is True

    def test_forbidden_pattern_present(self):
        v = ResponseValidator(ValidatorConfig(forbidden_patterns=["captcha"]))
        result = v.validate("please solve the captcha")
        assert result.valid is False
        assert "forbidden pattern" in result.reason

    def test_forbidden_pattern_absent(self):
        v = ResponseValidator(ValidatorConfig(forbidden_patterns=["captcha"]))
        result = v.validate("normal page content")
        assert result.valid is True

    def test_content_type_allowed(self):
        v = ResponseValidator(ValidatorConfig(allowed_content_types=["text/html"]))
        result = v.validate("body", content_type="text/html; charset=utf-8")
        assert result.valid is True

    def test_content_type_rejected(self):
        v = ResponseValidator(ValidatorConfig(allowed_content_types=["text/html"]))
        result = v.validate("body", content_type="application/json")
        assert result.valid is False
        assert "content-type" in result.reason

    def test_no_content_type_filter_passes_any(self, default_validator):
        result = default_validator.validate("body", content_type="application/xml")
        assert result.valid is True
