"""Tests for ResponseCacheStats."""
import pytest
from scrapewarden.response_cache_stats import ResponseCacheStats, _DomainCacheStats


@pytest.fixture
def stats() -> ResponseCacheStats:
    return ResponseCacheStats()


class TestDomainCacheStats:
    def test_initial_values(self):
        s = _DomainCacheStats()
        assert s.hits == 0
        assert s.misses == 0
        assert s.evictions == 0
        assert s.bytes_saved == 0

    def test_hit_rate_zero_when_no_requests(self):
        s = _DomainCacheStats()
        assert s.hit_rate == 0.0

    def test_hit_rate_all_hits(self):
        s = _DomainCacheStats(hits=10, misses=0)
        assert s.hit_rate == 1.0

    def test_hit_rate_mixed(self):
        s = _DomainCacheStats(hits=3, misses=1)
        assert s.hit_rate == pytest.approx(0.75)

    def test_to_dict_keys(self):
        s = _DomainCacheStats(hits=2, misses=1, evictions=0, bytes_saved=512)
        d = s.to_dict()
        assert set(d.keys()) == {"hits", "misses", "evictions", "bytes_saved", "hit_rate"}


class TestResponseCacheStats:
    def test_record_hit_increments(self, stats):
        stats.record_hit("example.com", bytes_saved=200)
        assert stats.total_hits() == 1
        assert stats.total_bytes_saved() == 200

    def test_record_miss_increments(self, stats):
        stats.record_miss("example.com")
        assert stats.total_misses() == 1

    def test_record_eviction(self, stats):
        stats.record_eviction("example.com")
        d = stats.domain_stats("example.com")
        assert d["evictions"] == 1

    def test_hit_rate_for_domain(self, stats):
        stats.record_hit("a.com")
        stats.record_hit("a.com")
        stats.record_miss("a.com")
        assert stats.hit_rate("a.com") == pytest.approx(2 / 3)

    def test_hit_rate_unknown_domain_is_zero(self, stats):
        assert stats.hit_rate("unknown.com") == 0.0

    def test_domain_stats_none_for_unknown(self, stats):
        assert stats.domain_stats("ghost.com") is None

    def test_domain_stats_returns_dict(self, stats):
        stats.record_hit("b.com", bytes_saved=100)
        d = stats.domain_stats("b.com")
        assert d is not None
        assert d["hits"] == 1
        assert d["bytes_saved"] == 100

    def test_multiple_domains_isolated(self, stats):
        stats.record_hit("x.com")
        stats.record_miss("y.com")
        assert stats.total_hits() == 1
        assert stats.total_misses() == 1
        assert stats.hit_rate("x.com") == 1.0
        assert stats.hit_rate("y.com") == 0.0

    def test_to_dict_structure(self, stats):
        stats.record_hit("z.com", bytes_saved=50)
        result = stats.to_dict()
        assert "domains" in result
        assert "total_hits" in result
        assert "total_misses" in result
        assert "total_bytes_saved" in result
        assert result["total_bytes_saved"] == 50

    def test_reset_clears_all(self, stats):
        stats.record_hit("c.com")
        stats.reset()
        assert stats.total_hits() == 0
        assert stats.domain_stats("c.com") is None
