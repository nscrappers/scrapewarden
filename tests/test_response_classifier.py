"""Tests for ResponseClassifier."""

import pytest
from scrapewarden.response_classifier import (
    ClassifierConfig,
    ResponseClass,
    ResponseClassifier,
)


class TestResponseClassifier:
    @pytest.fixture
    def classifier(self) -> ResponseClassifier:
        return ResponseClassifier()

    def test_200_is_success(self, classifier):
        assert classifier.classify(200) == ResponseClass.SUCCESS

    def test_201_is_success(self, classifier):
        assert classifier.classify(201) == ResponseClass.SUCCESS

    def test_429_is_soft_block(self, classifier):
        assert classifier.classify(429) == ResponseClass.SOFT_BLOCK

    def test_503_is_soft_block(self, classifier):
        assert classifier.classify(503) == ResponseClass.SOFT_BLOCK

    def test_403_is_hard_failure(self, classifier):
        assert classifier.classify(403) == ResponseClass.HARD_FAILURE

    def test_404_is_hard_failure(self, classifier):
        assert classifier.classify(404) == ResponseClass.HARD_FAILURE

    def test_500_is_transient_error(self, classifier):
        assert classifier.classify(500) == ResponseClass.TRANSIENT_ERROR

    def test_502_is_transient_error(self, classifier):
        assert classifier.classify(502) == ResponseClass.TRANSIENT_ERROR

    def test_captcha_in_body_triggers_soft_block(self, classifier):
        result = classifier.classify(200, body="Please solve the CAPTCHA to continue.")
        assert result == ResponseClass.SOFT_BLOCK

    def test_robot_pattern_in_body_triggers_soft_block(self, classifier):
        result = classifier.classify(200, body="Our systems detected unusual robot activity.")
        assert result == ResponseClass.SOFT_BLOCK

    def test_clean_200_body_is_success(self, classifier):
        result = classifier.classify(200, body="<html><body>Product page</body></html>")
        assert result == ResponseClass.SUCCESS

    def test_unknown_5xx_is_transient(self, classifier):
        assert classifier.classify(599) == ResponseClass.TRANSIENT_ERROR

    def test_unknown_4xx_is_hard_failure(self, classifier):
        assert classifier.classify(418) == ResponseClass.HARD_FAILURE

    def test_is_retryable_soft_block(self, classifier):
        assert classifier.is_retryable(ResponseClass.SOFT_BLOCK) is True

    def test_is_retryable_transient_error(self, classifier):
        assert classifier.is_retryable(ResponseClass.TRANSIENT_ERROR) is True

    def test_is_not_retryable_hard_failure(self, classifier):
        assert classifier.is_retryable(ResponseClass.HARD_FAILURE) is False

    def test_is_not_retryable_success(self, classifier):
        assert classifier.is_retryable(ResponseClass.SUCCESS) is False

    def test_should_rotate_proxy_on_soft_block(self, classifier):
        assert classifier.should_rotate_proxy(ResponseClass.SOFT_BLOCK) is True

    def test_should_not_rotate_proxy_on_transient_error(self, classifier):
        assert classifier.should_rotate_proxy(ResponseClass.TRANSIENT_ERROR) is False


class TestClassifierConfig:
    def test_from_dict_overrides_defaults(self):
        config = ClassifierConfig.from_dict({"soft_block_status_codes": [429, 430]})
        assert 430 in config.soft_block_status_codes
        assert 429 in config.soft_block_status_codes

    def test_custom_captcha_pattern(self):
        config = ClassifierConfig.from_dict({"captcha_body_patterns": ["verify you are human"]})
        classifier = ResponseClassifier(config)
        result = classifier.classify(200, body="Please verify you are human before continuing.")
        assert result == ResponseClass.SOFT_BLOCK
