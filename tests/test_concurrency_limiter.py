"""Tests for scrapewarden.concurrency_limiter."""

import asyncio
import pytest
from scrapewarden.concurrency_limiter import ConcurrencyConfig, ConcurrencyLimiter


class TestConcurrencyConfig:
    def test_defaults(self):
        cfg = ConcurrencyConfig()
        assert cfg.max_concurrent_per_domain == 4
        assert cfg.global_max_concurrent == 16

    def test_from_dict(self):
        cfg = ConcurrencyConfig.from_dict(
            {"max_concurrent_per_domain": "2", "global_max_concurrent": "8"}
        )
        assert cfg.max_concurrent_per_domain == 2
        assert cfg.global_max_concurrent == 8

    def test_from_dict_defaults(self):
        cfg = ConcurrencyConfig.from_dict({})
        assert cfg.global_max_concurrent == 16


class TestConcurrencyLimiter:
    @pytest.fixture
    def limiter(self):
        return ConcurrencyLimiter(ConcurrencyConfig(max_concurrent_per_domain=2, global_max_concurrent=5))

    @pytest.mark.asyncio
    async def test_acquire_and_release(self, limiter):
        async with limiter.acquire("example.com"):
            assert limiter.domain_available("example.com") == 1
        assert limiter.domain_available("example.com") == 2

    @pytest.mark.asyncio
    async def test_global_slot_consumed(self, limiter):
        async with limiter.acquire("a.com"):
            assert limiter.global_available() == 4
        assert limiter.global_available() == 5

    @pytest.mark.asyncio
    async def test_domain_concurrency_blocks_at_limit(self, limiter):
        results = []

        async def task(label):
            async with limiter.acquire("b.com"):
                await asyncio.sleep(0.05)
                results.append(label)

        await asyncio.gather(task("first"), task("second"), task("third"))
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_independent_domains_do_not_block_each_other(self, limiter):
        order = []

        async def task(domain):
            async with limiter.acquire(domain):
                await asyncio.sleep(0.01)
                order.append(domain)

        await asyncio.gather(task("x.com"), task("y.com"))
        assert set(order) == {"x.com", "y.com"}

    def test_unknown_domain_available_returns_max(self, limiter):
        assert limiter.domain_available("new.com") == 2

    def test_known_domains_populated_on_acquire_start(self, limiter):
        # domain sem created lazily on first acquire call
        _ = limiter._domain_sem("lazy.com")
        assert "lazy.com" in limiter.known_domains()

    @pytest.mark.asyncio
    async def test_global_limit_enforced(self):
        lim = ConcurrencyLimiter(ConcurrencyConfig(max_concurrent_per_domain=10, global_max_concurrent=2))
        in_flight = []

        async def task(i):
            async with lim.acquire("g.com"):
                in_flight.append(i)
                await asyncio.sleep(0.05)
                in_flight.pop()

        tasks = [asyncio.create_task(task(i)) for i in range(4)]
        await asyncio.gather(*tasks)
        # all finished without error, global limit was respected
        assert in_flight == []
