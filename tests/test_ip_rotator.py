"""Tests for scrapewarden.ip_rotator."""
from unittest.mock import patch
from datetime import datetime, timedelta

import pytest

from scrapewarden.ip_rotator import IPEntry, IPRotator, IPRotatorConfig


class TestIPEntry:
    def test_not_banned_by_default(self):
        entry = IPEntry(address="1.2.3.4")
        assert not entry.is_banned()

    def test_ban_after_three_failures(self):
        entry = IPEntry(address="1.2.3.4")
        entry.mark_failure()
        entry.mark_failure()
        assert not entry.is_banned()
        entry.mark_failure()
        assert entry.is_banned()

    def test_success_clears_ban(self):
        entry = IPEntry(address="1.2.3.4")
        for _ in range(3):
            entry.mark_failure()
        assert entry.is_banned()
        entry.mark_success()
        assert not entry.is_banned()
        assert entry.failure_count == 0

    def test_ban_expires(self):
        entry = IPEntry(address="1.2.3.4")
        for _ in range(3):
            entry.mark_failure(ban_duration_seconds=0.0)
        entry.banned_until = datetime.utcnow() - timedelta(seconds=1)
        assert not entry.is_banned()


class TestIPRotatorConfig:
    def test_defaults(self):
        cfg = IPRotatorConfig()
        assert cfg.ban_duration_seconds == 60.0
        assert cfg.strategy == "round_robin"

    def test_from_dict(self):
        cfg = IPRotatorConfig.from_dict({"ban_duration_seconds": 30, "strategy": "random"})
        assert cfg.ban_duration_seconds == 30.0
        assert cfg.strategy == "random"

    def test_from_dict_defaults(self):
        cfg = IPRotatorConfig.from_dict({})
        assert cfg.ban_duration_seconds == 60.0


class TestIPRotator:
    @pytest.fixture
    def rotator(self):
        return IPRotator(["10.0.0.1", "10.0.0.2", "10.0.0.3"])

    def test_next_ip_returns_address(self, rotator):
        ip = rotator.next_ip()
        assert ip in ["10.0.0.1", "10.0.0.2", "10.0.0.3"]

    def test_round_robin_cycles(self, rotator):
        ips = [rotator.next_ip() for _ in range(3)]
        assert set(ips) == {"10.0.0.1", "10.0.0.2", "10.0.0.3"}

    def test_banned_ip_skipped(self, rotator):
        for _ in range(3):
            rotator.report_failure("10.0.0.1")
        for _ in range(10):
            ip = rotator.next_ip()
            assert ip != "10.0.0.1"

    def test_all_banned_returns_none(self):
        rotator = IPRotator(["10.0.0.1"])
        for _ in range(3):
            rotator.report_failure("10.0.0.1")
        assert rotator.next_ip() is None

    def test_available_count(self, rotator):
        assert rotator.available_count() == 3
        for _ in range(3):
            rotator.report_failure("10.0.0.1")
        assert rotator.available_count() == 2

    def test_all_banned_flag(self):
        rotator = IPRotator(["10.0.0.1"])
        assert not rotator.all_banned()
        for _ in range(3):
            rotator.report_failure("10.0.0.1")
        assert rotator.all_banned()

    def test_random_strategy_returns_ip(self):
        cfg = IPRotatorConfig(strategy="random")
        rotator = IPRotator(["10.0.0.1", "10.0.0.2"], config=cfg)
        ip = rotator.next_ip()
        assert ip in ["10.0.0.1", "10.0.0.2"]

    def test_success_unblocks_ip(self, rotator):
        for _ in range(3):
            rotator.report_failure("10.0.0.1")
        assert rotator.available_count() == 2
        rotator.report_success("10.0.0.1")
        assert rotator.available_count() == 3
