import json
from pathlib import Path

import pytest

from syftbox.client.benchmark.netstats_tcp import HTTPMetrics, Stats, TCPTimingStats
from syftbox.client.benchmark.report import (
    ConsoleReport,
    JSONReport,
    NetworkBenchmarkResult,
    SyncPerformanceMetric,
)
from syftbox.client.benchmark.sync import DataTransferStats, PerformanceMetrics


@pytest.fixture
def aggregate_stats():
    """Fixture for aggregate statistics."""
    return Stats(min=10.0, max=20.0, mean=15.0, p50=15.0, stddev=2.0, p95=19.0, p99=19.5)


@pytest.fixture
def network_metric(aggregate_stats):
    """Fixture for network metric data."""
    return NetworkBenchmarkResult(
        timestamp="2024-01-01T00:00:00+00:00",
        num_runs=5,
        url="https://test.example.com",
        http_stats=HTTPMetrics(
            dns_time=aggregate_stats,
            connect_time=aggregate_stats,
            ssl_time=aggregate_stats,
            tcp_time=aggregate_stats,
            starttransfer_time=aggregate_stats,
            total_time=aggregate_stats,
            server_processing_time=aggregate_stats,
            content_transfer_time=aggregate_stats,
            success_rate=99.9,
        ),
        tcp_stats=TCPTimingStats(
            latency_stats=aggregate_stats,
            jitter_stats=aggregate_stats,
            connection_success_rate=98.5,
            requests_per_minute=1000,
            max_requests_per_minute=1200,
            max_concurrent_connections=100,
            requests_in_last_minute=950,
        ),
    )


@pytest.fixture
def performance_metrics():
    """Fixture for performance metrics."""
    return PerformanceMetrics(
        min_time=100.0,
        max_time=200.0,
        avg_time=150.0,
        median_time=150.0,
        stddev_time=25.0,
        p95=190.0,
        p99=198.0,
        success_rate=95.0,
    )


@pytest.fixture
def sync_metric(performance_metrics):
    """Fixture for sync performance metric data."""
    size_data = DataTransferStats(
        file_size_mb=5, upload_metrics=performance_metrics, download_metrics=performance_metrics
    )
    return SyncPerformanceMetric(size_metrics=[size_data], num_runs=5)


def test_json_report_generate(network_metric, sync_metric, tmp_path):
    """Test JSON report generation."""
    reporter = JSONReport()
    metrics = {"network": network_metric, "sync": sync_metric}

    report = reporter.generate(metrics)

    assert isinstance(report, dict)
    assert "metrics" in report
    assert "network" in report["metrics"]
    assert "sync" in report["metrics"]

    # Verify network metrics
    network_data = report["metrics"]["network"]
    assert network_data["url"] == "https://test.example.com"
    assert network_data["num_runs"] == 5

    # Verify sync metrics
    sync_data = report["metrics"]["sync"]
    assert len(sync_data["size_metrics"]) == 1
    assert sync_data["size_metrics"][0]["file_size_mb"] == 5


def test_json_report_save(network_metric, sync_metric, tmp_path):
    """Test JSON report saving to file."""
    reporter = JSONReport()
    metrics = {"network": network_metric, "sync": sync_metric}

    reporter.generate(metrics, tmp_path)

    report_file = tmp_path / "benchmark.json"
    assert report_file.exists()

    # Verify saved content
    saved_data = json.loads(report_file.read_text())
    assert "metrics" in saved_data
    assert "network" in saved_data["metrics"]
    assert "sync" in saved_data["metrics"]


def test_human_readable_report_generate(network_metric, sync_metric):
    """Test human readable report generation."""
    reporter = ConsoleReport()
    metrics = {"network": network_metric, "sync": sync_metric}

    report = reporter.generate(metrics)

    assert isinstance(report, str)
    # Check for key sections
    assert "Benchmark Report" in report
    assert "Network Metrics" in report
    assert "HTTP Statistics" in report
    assert "TCP Statistics" in report
    assert "Sync Performance Metrics" in report

    # Check for specific metrics
    assert "DNS lookup time" in report
    assert "Connection Time" in report
    assert "TCP Latency" in report
    assert "Size(MB)" in report
    assert "Operation" in report


def test_human_readable_report_save(network_metric, sync_metric, tmp_path):
    """Test human readable report saving to file."""
    reporter = ConsoleReport()
    metrics = {"network": network_metric, "sync": sync_metric}

    reporter.generate(metrics, tmp_path)

    report_file = tmp_path / "benchmark.txt"
    assert report_file.exists()

    # Verify saved content
    saved_content = report_file.read_text()
    assert "Benchmark Report" in saved_content
    assert "Network Metrics" in saved_content
    assert "Sync Performance Metrics" in saved_content


def test_dict_to_str_conversion():
    """Test dictionary to string conversion."""
    reporter = ConsoleReport()
    test_dict = {"key1": 100, "key2": 200}
    result = reporter.dict_to_str(test_dict)

    assert isinstance(result, str)
    assert "key1: 100" in result
    assert "key2: 200" in result


def test_empty_metrics():
    """Test report generation with empty metrics."""
    reporter = JSONReport()
    metrics = {}

    report = reporter.generate(metrics)
    assert report["metrics"] == {}


@pytest.mark.parametrize("reporter_class", [JSONReport, ConsoleReport])
def test_invalid_save_path(reporter_class, network_metric, sync_metric):
    """Test saving report to invalid path."""
    reporter = reporter_class()
    metrics = {"network": network_metric, "sync": sync_metric}

    invalid_path = Path("/nonexistent/directory")
    with pytest.raises(FileNotFoundError):
        reporter.generate(metrics, invalid_path)


def test_sync_metric_multiple_sizes(performance_metrics):
    """Test report with multiple file sizes."""
    size_data_1 = DataTransferStats(
        file_size_mb=1, upload_metrics=performance_metrics, download_metrics=performance_metrics
    )
    size_data_2 = DataTransferStats(
        file_size_mb=5, upload_metrics=performance_metrics, download_metrics=performance_metrics
    )

    sync_metric = SyncPerformanceMetric(size_metrics=[size_data_1, size_data_2], num_runs=5)

    reporter = ConsoleReport()
    report = reporter.generate({"sync": sync_metric})

    assert "1" in report  # Check for 1MB size
    assert "5" in report  # Check for 5MB size
