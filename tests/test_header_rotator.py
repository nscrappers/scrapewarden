"""Tests for scrapewarden.header_rotator."""

import pytest

from scrapewarden.header_rotator import (
    DEFAULT_USER_AGENTS,
    HeaderRotator,
    HeaderRotatorConfig,
)


class TestHeaderRotatorConfig:
    def test_defaults(self):
        cfg = HeaderRotatorConfig()
        assert cfg.user_agents == DEFAULT_USER_AGENTS
        assert cfg.rotate_accept_language is True
        assert cfg.extra_headers == {}

    def test_from_dict_custom_agents(self):
        agents = ["CustomBot/1.0", "CustomBot/2.0"]
        cfg = HeaderRotatorConfig.from_dict({"user_agents": agents})
        assert cfg.user_agents == agents

    def test_from_dict_disable_language_rotation(self):
        cfg = HeaderRotatorConfig.from_dict({"rotate_accept_language": False})
        assert cfg.rotate_accept_language is False

    def test_from_dict_extra_headers(self):
        cfg = HeaderRotatorConfig.from_dict({"extra_headers": {"X-Custom": "val"}})
        assert cfg.extra_headers == {"X-Custom": "val"}


class TestHeaderRotator:
    @pytest.fixture()
    def rotator(self):
        return HeaderRotator()

    def test_get_headers_contains_user_agent(self, rotator):
        headers = rotator.get_headers()
        assert "User-Agent" in headers

    def test_user_agent_is_from_pool(self, rotator):
        for _ in range(20):
            ua = rotator.get_headers()["User-Agent"]
            assert ua in DEFAULT_USER_AGENTS

    def test_accept_language_included_by_default(self, rotator):
        headers = rotator.get_headers()
        assert "Accept-Language" in headers

    def test_accept_language_omitted_when_disabled(self):
        cfg = HeaderRotatorConfig(rotate_accept_language=False)
        rotator = HeaderRotator(config=cfg)
        headers = rotator.get_headers()
        assert "Accept-Language" not in headers

    def test_extra_headers_included(self):
        cfg = HeaderRotatorConfig(extra_headers={"X-Token": "abc123"})
        rotator = HeaderRotator(config=cfg)
        headers = rotator.get_headers()
        assert headers["X-Token"] == "abc123"

    def test_apply_does_not_overwrite_existing(self, rotator):
        existing = {"User-Agent": "MyCustomAgent/1.0", "X-Foo": "bar"}
        merged = rotator.apply(existing)
        assert merged["User-Agent"] == "MyCustomAgent/1.0"
        assert merged["X-Foo"] == "bar"

    def test_apply_adds_missing_headers(self, rotator):
        merged = rotator.apply({})
        assert "User-Agent" in merged

    def test_user_agent_pool_size(self, rotator):
        assert rotator.user_agent_pool_size == len(DEFAULT_USER_AGENTS)

    def test_single_agent_always_returned(self):
        cfg = HeaderRotatorConfig(user_agents=["OnlyBot/1.0"])
        rotator = HeaderRotator(config=cfg)
        for _ in range(10):
            assert rotator.get_headers()["User-Agent"] == "OnlyBot/1.0"

    def test_empty_agent_list_omits_header(self):
        cfg = HeaderRotatorConfig(user_agents=[])
        rotator = HeaderRotator(config=cfg)
        headers = rotator.get_headers()
        assert "User-Agent" not in headers
