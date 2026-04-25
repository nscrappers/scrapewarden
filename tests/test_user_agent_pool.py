"""Tests for UserAgentPool and UserAgentPoolConfig."""
import pytest
from scrapewarden.user_agent_pool import UserAgentPool, UserAgentPoolConfig


class TestUserAgentPoolConfig:
    def test_defaults(self):
        cfg = UserAgentPoolConfig()
        assert len(cfg.agents) == 3
        assert cfg.weights is None
        assert cfg.avoid_repeat is True
        assert cfg.ban_on_consecutive_failures == 3

    def test_from_dict(self):
        cfg = UserAgentPoolConfig.from_dict({
            "agents": ["AgentA", "AgentB"],
            "weights": [0.7, 0.3],
            "avoid_repeat": False,
            "ban_on_consecutive_failures": 5,
        })
        assert cfg.agents == ["AgentA", "AgentB"]
        assert cfg.weights == [0.7, 0.3]
        assert cfg.avoid_repeat is False
        assert cfg.ban_on_consecutive_failures == 5

    def test_from_dict_defaults(self):
        cfg = UserAgentPoolConfig.from_dict({})
        assert len(cfg.agents) == 3
        assert cfg.ban_on_consecutive_failures == 3


@pytest.fixture
def pool():
    cfg = UserAgentPoolConfig(
        agents=["AgentA", "AgentB", "AgentC"],
        avoid_repeat=False,
    )
    return UserAgentPool(cfg)


class TestUserAgentPool:
    def test_pick_returns_string(self, pool):
        agent = pool.pick()
        assert isinstance(agent, str)
        assert agent in ["AgentA", "AgentB", "AgentC"]

    def test_active_count_starts_full(self, pool):
        assert pool.active_count == 3

    def test_ban_after_consecutive_failures(self, pool):
        for _ in range(3):
            pool.report_failure("AgentA")
        assert pool.active_count == 2

    def test_success_clears_ban(self, pool):
        for _ in range(3):
            pool.report_failure("AgentA")
        assert pool.active_count == 2
        pool.report_success("AgentA")
        assert pool.active_count == 3

    def test_usage_counts_increment(self, pool):
        for _ in range(5):
            agent = pool.pick()
        total = sum(pool.usage_counts.values())
        assert total == 5

    def test_avoid_repeat_skips_last(self):
        cfg = UserAgentPoolConfig(agents=["AgentX", "AgentY"], avoid_repeat=True)
        p = UserAgentPool(cfg)
        first = p.pick()
        second = p.pick()
        assert second != first

    def test_fallback_when_all_banned(self, pool):
        for agent in ["AgentA", "AgentB", "AgentC"]:
            for _ in range(3):
                pool.report_failure(agent)
        assert pool.active_count == 0
        # Should still return something without raising
        result = pool.pick()
        assert result in ["AgentA", "AgentB", "AgentC"]

    def test_weighted_selection_respected():
        cfg = UserAgentPoolConfig(
            agents=["OnlyAgent"],
            weights=[1.0],
            avoid_repeat=False,
        )
        p = UserAgentPool(cfg)
        assert p.pick() == "OnlyAgent"

    def test_report_unknown_agent_no_error(self, pool):
        pool.report_failure("NonExistentAgent")  # should not raise
        pool.report_success("NonExistentAgent")  # should not raise
