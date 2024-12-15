from datetime import datetime
from urllib.parse import urlparse

import pytest
import requests

from syftbox.client.benchmark.netstats_tcp import HTTPMetrics, Stats, TCPTimingStats
from syftbox.client.benchmark.network import NetworkBenchmark, NetworkBenchmarkResult


@pytest.fixture
def mock_datetime(monkeypatch):
    """Fixture to provide a consistent datetime for testing."""
    FAKE_TIME = "2024-01-01T00:00:00+00:00"

    class MockDatetime:
        @staticmethod
        def now(tz=None):
            return datetime.fromisoformat(FAKE_TIME)

    monkeypatch.setattr("syftbox.client.benchmark.network_metric.datetime", MockDatetime)
    return FAKE_TIME


@pytest.fixture
def mock_aggregate_stats():
    """Fixture to create mock aggregate stats."""
    return Stats(min=10.0, max=20.0, mean=15.0, p50=15.0, stddev=2.0, p95=19.0, p99=19.5)


@pytest.fixture
def config():
    class MockConfig:
        server_url = "https://test.example.com:8080"

    return MockConfig()


@pytest.fixture
def collector(config):
    return NetworkBenchmark(config)


def test_initialization(collector):
    """Test collector initialization."""
    assert collector.url == "https://test.example.com:8080"
    assert collector.tcp_perf is not None
    assert collector.http_perf is not None


def test_url_parsing(collector):
    """Test URL parsing and port detection."""
    parsed = urlparse(collector.url)
    assert parsed.hostname == "test.example.com"
    assert parsed.port == 8080


def test_default_port_http(monkeypatch):
    """Test default port assignment for HTTP."""

    class MockConfig:
        server_url = "http://test.example.com"

    collector = NetworkBenchmark(MockConfig())
    assert collector.tcp_perf.port == 80


def test_default_port_https(monkeypatch):
    """Test default port assignment for HTTPS."""

    class MockConfig:
        server_url = "https://test.example.com"

    collector = NetworkBenchmark(MockConfig())
    assert collector.tcp_perf.port == 443


def test_ping_success(collector, monkeypatch):
    """Test successful server ping."""

    class MockResponse:
        def raise_for_status(self):
            pass

    def mock_get(url):
        return MockResponse()

    monkeypatch.setattr(requests, "get", mock_get)
    assert collector.ping() is True


def test_ping_failure(collector, monkeypatch):
    """Test failed server ping."""

    def mock_get(url):
        raise requests.exceptions.RequestException("Connection failed")

    monkeypatch.setattr(requests, "get", mock_get)
    with pytest.raises(requests.exceptions.RequestException):
        collector.ping()


def test_collect_metrics_success(collector, monkeypatch, mock_datetime, mock_aggregate_stats):
    """Test successful metrics collection."""
    # Mock the ping method
    monkeypatch.setattr(collector, "ping", lambda: True)

    # Mock TCP stats
    class MockTCPStats:
        def get_stats(self, num_runs):
            return TCPTimingStats(
                latency_stats=mock_aggregate_stats,
                jitter_stats=mock_aggregate_stats,
                connection_success_rate=98.5,
                requests_per_minute=1000,
                max_requests_per_minute=1200,
                max_concurrent_connections=100,
                requests_in_last_minute=950,
            )

    # Mock HTTP stats
    class MockHTTPStats:
        def get_stats(self, num_runs):
            return HTTPMetrics(
                dns_time=mock_aggregate_stats,
                connect_time=mock_aggregate_stats,
                ssl_time=mock_aggregate_stats,
                starttransfer_time=mock_aggregate_stats,
                total_time=mock_aggregate_stats,
                tcp_time=mock_aggregate_stats,
                content_transfer_time=mock_aggregate_stats,
                server_processing_time=mock_aggregate_stats,
                success_rate=99.9,
            )

    monkeypatch.setattr(collector, "tcp_perf", MockTCPStats())
    monkeypatch.setattr(collector, "http_perf", MockHTTPStats())

    result = collector.collect_metrics(num_runs=5)

    assert isinstance(result, NetworkBenchmarkResult)
    assert result.timestamp == mock_datetime
    assert result.url == "https://test.example.com:8080"
    assert result.num_runs == 5

    # Verify TCP metrics structure
    assert isinstance(result.tcp_stats.latency_stats, Stats)
    assert result.tcp_stats.latency_stats.mean == 15.0
    assert result.tcp_stats.latency_stats.p95 == 19.0
    assert result.tcp_stats.connection_success_rate == 98.5
    assert result.tcp_stats.requests_per_minute == 1000

    # Verify HTTP metrics structure
    assert isinstance(result.http_stats.total_time, Stats)
    assert result.http_stats.total_time.mean == 15.0
    assert result.http_stats.total_time.p95 == 19.0
    assert result.http_stats.success_rate == 99.9


def test_collect_metrics_server_unreachable(collector, monkeypatch):
    """Test metrics collection when server is unreachable."""
    monkeypatch.setattr(collector, "ping", lambda: False)

    result = collector.collect_metrics(num_runs=5)
    assert isinstance(result, dict)
    assert "error" in result
    assert result["error"] == f"Server: {collector.url} is not reachable."


def test_collect_metrics_with_errors(collector, monkeypatch):
    """Test metrics collection with TCP/HTTP errors."""
    monkeypatch.setattr(collector, "ping", lambda: True)

    class MockTCPStatsWithError:
        def get_stats(self, num_runs):
            raise ConnectionError("TCP connection failed")

    monkeypatch.setattr(collector, "tcp_perf", MockTCPStatsWithError())

    with pytest.raises(ConnectionError, match="TCP connection failed"):
        collector.collect_metrics(num_runs=5)


@pytest.mark.parametrize("num_runs", [1, 5, 10])
def test_collect_metrics_different_runs(collector, monkeypatch, mock_aggregate_stats, num_runs):
    """Test metrics collection with different numbers of runs."""
    monkeypatch.setattr(collector, "ping", lambda: True)

    runs_count = []

    class MockTCPStats:
        def get_stats(self, num_runs):
            runs_count.append(num_runs)
            return TCPTimingStats(
                latency_stats=mock_aggregate_stats,
                jitter_stats=mock_aggregate_stats,
                connection_success_rate=98.5,
                requests_per_minute=1000,
                max_requests_per_minute=1200,
                max_concurrent_connections=100,
                requests_in_last_minute=950,
            )

    class MockHTTPStats:
        def get_stats(self, num_runs):
            runs_count.append(num_runs)
            return HTTPMetrics(
                dns_time=mock_aggregate_stats,
                connect_time=mock_aggregate_stats,
                ssl_time=mock_aggregate_stats,
                starttransfer_time=mock_aggregate_stats,
                total_time=mock_aggregate_stats,
                tcp_time=mock_aggregate_stats,
                content_transfer_time=mock_aggregate_stats,
                server_processing_time=mock_aggregate_stats,
                success_rate=99.9,
            )

    monkeypatch.setattr(collector, "tcp_perf", MockTCPStats())
    monkeypatch.setattr(collector, "http_perf", MockHTTPStats())

    result = collector.collect_metrics(num_runs=num_runs)

    assert result.num_runs == num_runs
    assert all(count == num_runs for count in runs_count)
    assert isinstance(result.tcp_stats, TCPTimingStats)
    assert isinstance(result.http_stats, HTTPMetrics)
