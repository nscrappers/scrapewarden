import time
import pytest
from scrapewarden.proxy_rotator import ProxyEntry, ProxyRotator


PROXY_URLS = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080",
    "http://proxy3.example.com:8080",
]


class TestProxyEntry:
    def test_not_banned_by_default(self):
        entry = ProxyEntry(url="http://proxy.example.com")
        assert not entry.is_banned

    def test_ban_after_three_failures(self):
        entry = ProxyEntry(url="http://proxy.example.com")
        for _ in range(3):
            entry.mark_failure(ban_duration=60.0)
        assert entry.is_banned

    def test_success_clears_ban(self):
        entry = ProxyEntry(url="http://proxy.example.com")
        for _ in range(3):
            entry.mark_failure(ban_duration=60.0)
        assert entry.is_banned
        entry.mark_success()
        assert not entry.is_banned
        assert entry.fail_count == 0


class TestProxyRotator:
    def test_from_list_creates_entries(self):
        rotator = ProxyRotator.from_list(PROXY_URLS)
        assert rotator.total_count == 3
        assert rotator.available_count == 3

    def test_round_robin_cycles(self):
        rotator = ProxyRotator.from_list(PROXY_URLS, strategy="round_robin")
        seen = [rotator.get_proxy().url for _ in range(3)]
        assert set(seen) == set(PROXY_URLS)

    def test_random_strategy_returns_proxy(self):
        rotator = ProxyRotator.from_list(PROXY_URLS, strategy="random")
        proxy = rotator.get_proxy()
        assert proxy is not None
        assert proxy.url in PROXY_URLS

    def test_least_used_strategy(self):
        rotator = ProxyRotator.from_list(PROXY_URLS, strategy="least_used")
        first = rotator.get_proxy()
        second = rotator.get_proxy()
        assert first is not None
        assert second is not None

    def test_report_failure_bans_proxy(self):
        rotator = ProxyRotator.from_list([PROXY_URLS[0]], ban_duration=60.0)
        for _ in range(3):
            rotator.report_failure(PROXY_URLS[0])
        assert rotator.available_count == 0

    def test_report_success_unbans_proxy(self):
        rotator = ProxyRotator.from_list([PROXY_URLS[0]], ban_duration=60.0)
        for _ in range(3):
            rotator.report_failure(PROXY_URLS[0])
        assert rotator.available_count == 0
        rotator.report_success(PROXY_URLS[0])
        assert rotator.available_count == 1

    def test_get_proxy_returns_none_when_all_banned(self):
        rotator = ProxyRotator.from_list(PROXY_URLS, ban_duration=60.0)
        for url in PROXY_URLS:
            for _ in range(3):
                rotator.report_failure(url)
        assert rotator.get_proxy() is None

    def test_banned_proxy_recovers_after_duration(self):
        rotator = ProxyRotator.from_list([PROXY_URLS[0]], ban_duration=0.05)
        for _ in range(3):
            rotator.report_failure(PROXY_URLS[0])
        assert rotator.available_count == 0
        time.sleep(0.1)
        assert rotator.available_count == 1
